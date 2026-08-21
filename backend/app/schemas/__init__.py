from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid
from app.models import ExperienceLevel, MilestoneType


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None


# Auth schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime


# Profile schemas
class LearnerProfileBase(BaseModel):
    interests: List[str] = Field(default_factory=list)
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    goals: str = ""
    target_role: Optional[str] = None
    time_commitment_hours: Optional[int] = Field(default=None, ge=1, le=40)
    learning_style: Optional[str] = None


class LearnerProfileCreate(LearnerProfileBase):
    pass


class LearnerProfileUpdate(LearnerProfileBase):
    completed_course_ids: List[uuid.UUID] = Field(default_factory=list)


class LearnerProfileResponse(LearnerProfileBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    completed_course_ids: List[uuid.UUID]
    created_at: datetime
    updated_at: datetime


# Course schemas
class CourseBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str
    domain: str = Field(min_length=1, max_length=100)
    difficulty: ExperienceLevel = ExperienceLevel.BEGINNER
    duration_hours: int = Field(default=0, ge=0)
    prerequisites: List[uuid.UUID] = Field(default_factory=list)
    skills_covered: List[str] = Field(default_factory=list)
    provider: Optional[str] = None
    url: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(CourseBase):
    pass


class CourseResponse(CourseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Learning Path schemas
class PathNodeBase(BaseModel):
    course_id: uuid.UUID
    order_index: int
    milestone_type: MilestoneType = MilestoneType.FOUNDATION


class PathNodeCreate(PathNodeBase):
    pass


class PathNodeUpdate(BaseModel):
    is_completed: Optional[bool] = None
    notes: Optional[str] = None


class PathNodeResponse(PathNodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    path_id: uuid.UUID
    is_completed: bool
    completed_at: Optional[datetime]
    notes: Optional[str]
    course: Optional[CourseResponse] = None


class LearningPathBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str
    estimated_weeks: Optional[int] = Field(default=None, ge=1, le=52)


class LearningPathCreate(LearningPathBase):
    nodes: List[PathNodeCreate] = Field(default_factory=list)


class LearningPathUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class LearningPathResponse(LearningPathBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    nodes: List[PathNodeResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# Chat schemas
class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|tool)$")
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: uuid.UUID
    tool_calls: Optional[List[dict]] = None


# Recommendation schemas
class RecommendationRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)
    domain: Optional[str] = None
    difficulty: Optional[ExperienceLevel] = None


class RecommendationItem(BaseModel):
    course: CourseResponse
    score: float = Field(ge=0, le=1)
    reason: str


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem]


# Dashboard schemas
class SkillProgress(BaseModel):
    skill: str
    level: float = Field(ge=0, le=1)
    courses_completed: int
    courses_total: int


class MilestoneProgress(BaseModel):
    milestone_type: MilestoneType
    completed: int
    total: int
    courses: List[CourseResponse]


class DashboardResponse(BaseModel):
    user: UserResponse
    profile: LearnerProfileResponse
    active_path: Optional[LearningPathResponse] = None
    skill_progress: List[SkillProgress] = Field(default_factory=list)
    milestones: List[MilestoneProgress] = Field(default_factory=list)
    next_actions: List[CourseResponse] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


# Profile Analysis schemas
class ProfileAnalysisRequest(BaseModel):
    natural_language_goals: str


class ProfileAnalysisResponse(BaseModel):
    interests: List[str]
    experience_level: ExperienceLevel
    goals: str
    target_role: Optional[str]
    time_commitment_hours: Optional[int]
    learning_style: Optional[str]
    suggested_domains: List[str]