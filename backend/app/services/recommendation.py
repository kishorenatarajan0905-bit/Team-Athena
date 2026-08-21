import structlog
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector
from app.models import Course, LearnerProfile, ExperienceLevel
from app.schemas import RecommendationItem, RecommendationResponse, CourseResponse
from app.services.embeddings import cosine_similarity, embed_profile
from app.core.database import Base

logger = structlog.get_logger()


def difficulty_score(learner_level: ExperienceLevel, course_level: ExperienceLevel) -> float:
    """Calculate difficulty match score (0-1)."""
    levels = [ExperienceLevel.BEGINNER, ExperienceLevel.INTERMEDIATE, ExperienceLevel.ADVANCED]
    learner_idx = levels.index(learner_level)
    course_idx = levels.index(course_level)

    diff = abs(learner_idx - course_idx)
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.7
    else:
        return 0.3


def prerequisite_satisfaction(
    learner_completed: List[UUID],
    course_prereqs: List[UUID]
) -> float:
    """Calculate prerequisite satisfaction score (0-1)."""
    if not course_prereqs:
        return 1.0

    completed_set = set(str(c) for c in learner_completed)
    prereq_set = set(str(c) for c in course_prereqs)
    satisfied = len(completed_set & prereq_set)
    return satisfied / len(prereq_set)


async def get_recommendations(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10,
    domain: Optional[str] = None,
    difficulty: Optional[ExperienceLevel] = None,
) -> RecommendationResponse:
    """Get personalized course recommendations for a learner."""
    # Get learner profile
    result = await db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile or not profile.skill_embedding:
        # Cold start: return popular/high-rated courses
        return await get_cold_start_recommendations(db, limit, domain, difficulty)

    # Get candidate courses
    query = select(Course).where(Course.embedding.is_not(None))

    if domain:
        query = query.where(Course.domain == domain)
    if difficulty:
        query = query.where(Course.difficulty == difficulty)

    # Exclude already completed courses
    if profile.completed_course_ids:
        query = query.where(Course.id.not_in(profile.completed_course_ids))

    result = await db.execute(query.limit(100))  # Fetch more for ranking
    candidates = result.scalars().all()

    if not candidates:
        return RecommendationResponse(recommendations=[])

    # Score each candidate
    scored = []
    learner_embedding = profile.skill_embedding

    for course in candidates:
        if not course.embedding:
            continue

        # Semantic similarity (0-1)
        sim_score = cosine_similarity(learner_embedding, course.embedding)
        sim_score = max(0, (sim_score + 1) / 2)  # Normalize from [-1,1] to [0,1]

        # Difficulty match
        diff_score = difficulty_score(profile.experience_level, course.difficulty)

        # Prerequisite satisfaction
        prereq_score = prerequisite_satisfaction(
            profile.completed_course_ids,
            course.prerequisites or []
        )

        # Combined score (weighted)
        final_score = (
            0.5 * sim_score +
            0.2 * diff_score +
            0.3 * prereq_score
        )

        # Generate reason
        reasons = []
        if sim_score > 0.7:
            reasons.append("matches your interests and skills")
        if diff_score > 0.8:
            reasons.append("appropriate difficulty for your level")
        if prereq_score == 1.0:
            reasons.append("you have all prerequisites")
        elif prereq_score > 0.5:
            reasons.append("you have most prerequisites")

        reason = "; ".join(reasons) if reasons else "relevant to your profile"

        scored.append(RecommendationItem(
            course=CourseResponse.model_validate(course),
            score=final_score,
            reason=reason
        ))

    # Sort by score and return top-k
    scored.sort(key=lambda x: x.score, reverse=True)
    return RecommendationResponse(recommendations=scored[:limit])


async def get_cold_start_recommendations(
    db: AsyncSession,
    limit: int,
    domain: Optional[str] = None,
    difficulty: Optional[ExperienceLevel] = None,
) -> RecommendationResponse:
    """Get recommendations for new users without profile."""
    query = select(Course).where(Course.rating.is_not(None)).order_by(Course.rating.desc())

    if domain:
        query = query.where(Course.domain == domain)
    if difficulty:
        query = query.where(Course.difficulty == difficulty)

    result = await db.execute(query.limit(limit))
    courses = result.scalars().all()

    recommendations = [
        RecommendationItem(
            course=CourseResponse.model_validate(c),
            score=0.5,
            reason="Popular course for new learners"
        )
        for c in courses
    ]

    return RecommendationResponse(recommendations=recommendations)


async def explain_recommendation(
    db: AsyncSession,
    user_id: UUID,
    course_id: UUID,
) -> str:
    """Generate detailed explanation for why a course was recommended."""
    # Get profile and course
    profile_result = await db.execute(
        select(LearnerProfile).where(LearnerProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()

    if not profile or not course:
        return "Unable to generate explanation."

    reasons = []

    # Interest match
    course_skills = set(course.skills_covered or [])
    user_interests = set(profile.interests or [])
    if course_skills & user_interests:
        matched = course_skills & user_interests
        reasons.append(f"This course covers {', '.join(matched)} which matches your interests.")

    # Skill gap
    if profile.skill_embedding and course.embedding:
        from app.services.embeddings import cosine_similarity
        sim = cosine_similarity(profile.skill_embedding, course.embedding)
        if sim > 0.6:
            reasons.append("The course content aligns well with your current skill vector.")

    # Prerequisites
    completed = set(str(c) for c in (profile.completed_course_ids or []))
    prereqs = set(str(c) for c in (course.prerequisites or []))
    if prereqs:
        missing = prereqs - completed
        if not missing:
            reasons.append("You have completed all prerequisites for this course.")
        elif len(missing) < len(prereqs):
            reasons.append(f"You have {len(prereqs) - len(missing)} of {len(prereqs)} prerequisites.")

    # Difficulty
    if profile.experience_level == course.difficulty:
        reasons.append(f"This {course.difficulty.value}-level course matches your current experience level.")

    # Goal alignment
    if profile.target_role and profile.target_role.lower() in course.description.lower():
        reasons.append(f"This course is relevant for your target role: {profile.target_role}.")

    return " ".join(reasons) if reasons else "This course was recommended based on your overall profile."