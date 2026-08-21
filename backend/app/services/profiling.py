import structlog
import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.nvidia_client import nvidia_client
from app.models import User, LearnerProfile, ExperienceLevel
from app.schemas import ProfileAnalysisResponse
from app.services.embeddings import embed_profile

logger = structlog.get_logger()


PROFILE_ANALYSIS_SYSTEM_PROMPT = """You are an expert learning coach. Analyze the user's natural language description of their learning goals and extract a structured profile.

Extract the following information:
1. interests: List of 3-8 specific topics/technologies they're interested in
2. experience_level: One of "beginner", "intermediate", "advanced"
3. goals: A concise summary of their learning objectives (1-2 sentences)
4. target_role: Specific job role they're targeting (if mentioned)
5. time_commitment_hours: Weekly hours they can commit (if mentioned)
6. learning_style: Preferred learning approach (e.g., "hands-on", "theoretical", "project-based", "video") (if mentioned)
7. suggested_domains: 3-5 relevant course domains based on their goals

Return ONLY valid JSON matching the ProfileAnalysisResponse schema."""


PROFILE_ANALYSIS_TOOLS = [{
    "type": "function",
    "function": {
        "name": "extract_learner_profile",
        "description": "Extract structured learner profile from natural language",
        "parameters": {
            "type": "object",
            "properties": {
                "interests": {"type": "array", "items": {"type": "string"}},
                "experience_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                "goals": {"type": "string"},
                "target_role": {"type": "string"},
                "time_commitment_hours": {"type": "integer"},
                "learning_style": {"type": "string"},
                "suggested_domains": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["interests", "experience_level", "goals", "suggested_domains"],
        },
    },
}]


async def analyze_profile_natural_language(text: str) -> ProfileAnalysisResponse:
    """Use LLM to analyze natural language goals into structured profile."""
    messages = [
        {"role": "system", "content": PROFILE_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this learner's goals: {text}"},
    ]

    response = await nvidia_client.chat_completion(
        messages=messages,
        tools=PROFILE_ANALYSIS_TOOLS,
        tool_choice="required",
        temperature=0.2,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)

    return ProfileAnalysisResponse(**args)


async def get_or_create_profile(db: AsyncSession, user_id: UUID) -> LearnerProfile:
    """Get existing profile or create empty one."""
    result = await db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = LearnerProfile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


async def update_profile(
    db: AsyncSession,
    user_id: UUID,
    interests: Optional[List[str]] = None,
    experience_level: Optional[ExperienceLevel] = None,
    goals: Optional[str] = None,
    target_role: Optional[str] = None,
    time_commitment_hours: Optional[int] = None,
    learning_style: Optional[str] = None,
    completed_course_ids: Optional[List[UUID]] = None,
) -> LearnerProfile:
    """Update learner profile and regenerate embedding."""
    profile = await get_or_create_profile(db, user_id)

    if interests is not None:
        profile.interests = interests
    if experience_level is not None:
        profile.experience_level = experience_level
    if goals is not None:
        profile.goals = goals
    if target_role is not None:
        profile.target_role = target_role
    if time_commitment_hours is not None:
        profile.time_commitment_hours = time_commitment_hours
    if learning_style is not None:
        profile.learning_style = learning_style
    if completed_course_ids is not None:
        profile.completed_course_ids = completed_course_ids

    # Regenerate skill embedding
    try:
        profile.skill_embedding = await embed_profile(profile)
    except Exception as e:
        logger.warning("profile_embedding_failed", error=str(e), user_id=str(user_id))

    await db.commit()
    await db.refresh(profile)
    return profile


async def add_completed_course(db: AsyncSession, user_id: UUID, course_id: UUID) -> LearnerProfile:
    """Add a completed course to learner's profile."""
    profile = await get_or_create_profile(db, user_id)

    if course_id not in profile.completed_course_ids:
        profile.completed_course_ids = list(profile.completed_course_ids) + [course_id]
        try:
            profile.skill_embedding = await embed_profile(profile)
        except Exception as e:
            logger.warning("profile_embedding_failed", error=str(e))
        await db.commit()
        await db.refresh(profile)

    return profile


async def get_profile_with_user(db: AsyncSession, user_id: UUID):
    """Get profile with user info."""
    result = await db.execute(
        select(User, LearnerProfile)
        .join(LearnerProfile, User.id == LearnerProfile.user_id, isouter=True)
        .where(User.id == user_id)
    )
    return result.first()