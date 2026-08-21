import structlog
from typing import List, Optional
import numpy as np
from app.core.nvidia_client import nvidia_client

logger = structlog.get_logger()


EMBEDDING_DIM = 3072


async def get_embedding(text: str) -> List[float]:
    """Get embedding for a single text."""
    try:
        return await nvidia_client.embedding(text)
    except Exception as e:
        logger.error("get_embedding_failed", error=str(e))
        raise


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings for multiple texts."""
    try:
        return await nvidia_client.embeddings(texts)
    except Exception as e:
        logger.error("get_embeddings_failed", error=str(e), count=len(texts))
        raise


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def build_course_text(course) -> str:
    """Build text representation of course for embedding."""
    parts = [
        f"Title: {course.title}",
        f"Description: {course.description}",
        f"Domain: {course.domain}",
        f"Difficulty: {course.difficulty.value}",
        f"Skills: {', '.join(course.skills_covered)}",
    ]
    return "\n".join(parts)


def build_profile_text(profile) -> str:
    """Build text representation of learner profile for embedding."""
    parts = [
        f"Interests: {', '.join(profile.interests)}",
        f"Experience Level: {profile.experience_level.value}",
        f"Goals: {profile.goals}",
    ]
    if profile.target_role:
        parts.append(f"Target Role: {profile.target_role}")
    if profile.learning_style:
        parts.append(f"Learning Style: {profile.learning_style}")
    return "\n".join(parts)


async def embed_course(course) -> List[float]:
    """Generate embedding for a course."""
    text = build_course_text(course)
    return await get_embedding(text)


async def embed_profile(profile) -> List[float]:
    """Generate embedding for a learner profile."""
    text = build_profile_text(profile)
    return await get_embedding(text)


async def embed_courses_batch(courses: List) -> List[List[float]]:
    """Generate embeddings for multiple courses in batch."""
    texts = [build_course_text(c) for c in courses]
    return await get_embeddings(texts)