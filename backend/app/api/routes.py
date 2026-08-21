from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
from app.core.database import get_db
from app.core.security import create_access_token, decode_token, verify_password, get_password_hash
from app.models import User, LearningPath, PathNode, ProgressTracking, Course, MilestoneType
from app.schemas import (
    UserRegister, UserLogin, UserResponse, Token,
    LearnerProfileResponse, LearnerProfileUpdate,
    ProfileAnalysisRequest, ProfileAnalysisResponse,
    RecommendationRequest, RecommendationResponse,
    LearningPathCreate, LearningPathResponse, PathNodeUpdate,
    ChatRequest, ChatResponse,
    DashboardResponse, CourseResponse,
)
from app.services import (
    get_or_create_profile, update_profile, add_completed_course,
    get_recommendations, explain_recommendation,
    generate_learning_path, get_learning_path, mark_node_complete,
    get_next_recommendations, AIAssistant, analyze_profile_natural_language,
)
from sqlalchemy import select
from typing import List

router = APIRouter()


# Auth dependency
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str = None,
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# Auth endpoints
@router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create empty profile
    from app.services import get_or_create_profile
    await get_or_create_profile(db, user.id)

    # Create token
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


@router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


# Profile endpoints
@router.get("/profile", response_model=LearnerProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(db, current_user.id)
    return profile


@router.put("/profile", response_model=LearnerProfileResponse)
async def update_profile_endpoint(
    profile_data: LearnerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import ExperienceLevel
    profile = await update_profile(
        db,
        current_user.id,
        interests=profile_data.interests,
        experience_level=profile_data.experience_level,
        goals=profile_data.goals,
        target_role=profile_data.target_role,
        time_commitment_hours=profile_data.time_commitment_hours,
        learning_style=profile_data.learning_style,
        completed_course_ids=profile_data.completed_course_ids,
    )
    return profile


@router.post("/profile/analyze", response_model=ProfileAnalysisResponse)
async def analyze_profile(
    request: ProfileAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await analyze_profile_natural_language(request.natural_language_goals)
    return analysis


# Recommendation endpoints
@router.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations_endpoint(
    limit: int = 10,
    domain: str = None,
    difficulty: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import ExperienceLevel
    diff = ExperienceLevel(difficulty) if difficulty else None
    return await get_recommendations(db, current_user.id, limit, domain, diff)


@router.get("/recommendations/{course_id}/explain")
async def explain_recommendation_endpoint(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    explanation = await explain_recommendation(db, current_user.id, course_id)
    return {"explanation": explanation}


# Learning Path endpoints
@router.post("/paths/generate", response_model=LearningPathResponse)
async def generate_path(
    path_data: LearningPathCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.path_generator import generate_learning_path, get_learning_path
    from uuid import UUID as UUIDType

    target_ids = [UUIDType(n.course_id) for n in path_data.nodes] if path_data.nodes else None

    path = await generate_learning_path(
        db,
        current_user.id,
        path_data.title,
        path_data.description,
        target_ids,
    )
    full_path = await get_learning_path(db, path.id)
    return full_path


@router.get("/paths", response_model=List[LearningPathResponse])
async def list_paths(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LearningPath)
        .where(LearningPath.user_id == current_user.id)
        .order_by(LearningPath.created_at.desc())
    )
    paths = result.scalars().all()

    # Load nodes for each path
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(LearningPath)
        .options(selectinload(LearningPath.nodes).selectinload(PathNode.course))
        .where(LearningPath.user_id == current_user.id)
        .order_by(LearningPath.created_at.desc())
    )
    paths = result.scalars().all()
    return paths


@router.get("/paths/{path_id}", response_model=LearningPathResponse)
async def get_path(
    path_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await get_learning_path(db, path_id)
    if not path or path.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Path not found")
    return path


@router.patch("/paths/{path_id}/nodes/{node_id}")
async def update_path_node(
    path_id: UUID,
    node_id: UUID,
    node_data: PathNodeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.path_generator import mark_node_complete

    path = await get_learning_path(db, path_id)
    if not path or path.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Path not found")

    if node_data.is_completed is True:
        node = await mark_node_complete(db, path_id, node_id)
        if node:
            await add_completed_course(db, current_user.id, node.course_id)
            return {"success": True, "message": "Course marked as complete"}

    return {"success": False, "message": "Invalid update"}


@router.get("/paths/{path_id}/next", response_model=List)
async def get_next_actions(
    path_id: UUID,
    limit: int = 3,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await get_learning_path(db, path_id)
    if not path or path.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Path not found")

    courses = await get_next_recommendations(db, path_id, limit)
    return courses


# Chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assistant = AIAssistant(db, current_user.id)
    return await assistant.chat(request)


# Dashboard endpoint
@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import LearningPath, PathNode, ProgressTracking, Course
    from sqlalchemy.orm import selectinload

    # Get profile
    profile = await get_or_create_profile(db, current_user.id)

    # Get active learning path
    result = await db.execute(
        select(LearningPath)
        .options(selectinload(LearningPath.nodes).selectinload(PathNode.course))
        .where(LearningPath.user_id == current_user.id, LearningPath.status == "active")
        .order_by(LearningPath.created_at.desc())
    )
    active_path = result.scalars().first()

    # Get progress tracking
    result = await db.execute(
        select(ProgressTracking)
        .where(ProgressTracking.user_id == current_user.id)
    )
    progress_records = result.scalars().all()

    # Calculate skill progress
    skill_progress = {}
    for record in progress_records:
        result = await db.execute(select(Course).where(Course.id == record.course_id))
        course = result.scalar_one_or_none()
        if course:
            for skill in course.skills_covered:
                if skill not in skill_progress:
                    skill_progress[skill] = {"completed": 0, "total": 0, "level": 0.0}
                skill_progress[skill]["total"] += 1
                if record.progress_pct >= 1.0:
                    skill_progress[skill]["completed"] += 1

    skill_progress_list = [
        {
            "skill": skill,
            "level": data["completed"] / data["total"] if data["total"] > 0 else 0,
            "courses_completed": data["completed"],
            "courses_total": data["total"],
        }
        for skill, data in skill_progress.items()
    ]

    # Calculate milestones
    from app.models import MilestoneType
    milestones = []
    if active_path:
        for m_type in [m.value for m in MilestoneType]:
            milestone_nodes = [n for n in active_path.nodes if n.milestone_type.value == m_type]
            if milestone_nodes:
                completed = sum(1 for n in milestone_nodes if n.is_completed)
                milestones.append({
                    "milestone_type": m_type,
                    "completed": completed,
                    "total": len(milestone_nodes),
                    "courses": [CourseResponse.model_validate(n.course).model_dump() for n in milestone_nodes if n.course],
                })

    # Get next actions
    next_actions = []
    if active_path:
        next_courses = await get_next_recommendations(db, active_path.id, 5)
        next_actions = [CourseResponse.model_validate(c).model_dump() for c in next_courses]

    # Stats
    completed_courses = len(profile.completed_course_ids or [])
    in_progress = sum(1 for r in progress_records if 0 < r.progress_pct < 1)
    total_paths_result = await db.execute(
        select(LearningPath).where(LearningPath.user_id == current_user.id)
    )
    total_paths = len(total_paths_result.scalars().all())

    return DashboardResponse(
        user=UserResponse.model_validate(current_user),
        profile=profile,
        active_path=active_path,
        skill_progress=skill_progress_list,
        milestones=milestones,
        next_actions=next_actions,
        stats={
            "completed_courses": completed_courses,
            "in_progress_courses": in_progress,
            "total_paths": total_paths,
            "active_path_weeks": active_path.estimated_weeks if active_path else 0,
        },
    )