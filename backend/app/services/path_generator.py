import structlog
from typing import List, Optional, Dict, Set
from uuid import UUID
from collections import defaultdict, deque
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Course, LearningPath, PathNode, MilestoneType, ExperienceLevel
from app.schemas import LearningPathCreate, PathNodeCreate
from app.services.recommendation import get_recommendations

logger = structlog.get_logger()


MILESTONE_ORDER = [
    MilestoneType.FOUNDATION,
    MilestoneType.CORE,
    MilestoneType.SPECIALIZATION,
    MilestoneType.CAPSTONE,
]


def topological_sort(courses: List[Course]) -> List[Course]:
    """Sort courses by prerequisites using Kahn's algorithm."""
    # Build adjacency list and in-degree count
    course_map = {c.id: c for c in courses}
    adj: Dict[UUID, List[UUID]] = defaultdict(list)
    in_degree: Dict[UUID, int] = defaultdict(int)

    for course in courses:
        for prereq_id in (course.prerequisites or []):
            if prereq_id in course_map:
                adj[prereq_id].append(course.id)
                in_degree[course.id] += 1
        if course.id not in in_degree:
            in_degree[course.id] = 0

    # Kahn's algorithm
    queue = deque([cid for cid, deg in in_degree.items() if deg == 0])
    result = []

    while queue:
        cid = queue.popleft()
        result.append(course_map[cid])
        for neighbor in adj[cid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycles
    if len(result) != len(courses):
        logger.warning("cycle_detected_in_prerequisites", remaining=len(courses) - len(result))
        # Add remaining courses (cycle detected)
        remaining = [c for c in courses if c.id not in [r.id for r in result]]
        result.extend(remaining)

    return result


def assign_milestones(courses: List[Course], num_milestones: int = 4) -> List[MilestoneType]:
    """Assign milestone types to courses based on position and difficulty."""
    if not courses:
        return []

    # Sort by difficulty first, then by position
    sorted_courses = sorted(courses, key=lambda c: (
        [ExperienceLevel.BEGINNER, ExperienceLevel.INTERMEDIATE, ExperienceLevel.ADVANCED].index(c.difficulty),
        courses.index(c)
    ))

    milestones = []
    chunk_size = max(1, len(sorted_courses) // num_milestones)

    for i, course in enumerate(sorted_courses):
        milestone_idx = min(i // chunk_size, len(MILESTONE_ORDER) - 1)
        milestones.append(MILESTONE_ORDER[milestone_idx])

    # Map back to original order
    course_to_milestone = {c.id: m for c, m in zip(sorted_courses, milestones)}
    return [course_to_milestone[c.id] for c in courses]


def estimate_weeks(courses: List[Course], hours_per_week: int = 10) -> int:
    """Estimate total weeks to complete the learning path."""
    total_hours = sum(c.duration_hours or 0 for c in courses)
    return max(1, (total_hours + hours_per_week - 1) // hours_per_week)


async def generate_learning_path(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    description: str,
    target_course_ids: Optional[List[UUID]] = None,
    hours_per_week: int = 10,
) -> LearningPath:
    """Generate a structured learning path for a learner."""

    # Get target courses - either provided or from recommendations
    if target_course_ids:
        result = await db.execute(
            select(Course).where(Course.id.in_(target_course_ids))
        )
        target_courses = list(result.scalars().all())
    else:
        # Get recommendations
        rec_response = await get_recommendations(db, user_id, limit=15)
        target_courses = [r.course for r in rec_response.recommendations]

    if not target_courses:
        raise ValueError("No target courses available for path generation")

    # Get all prerequisites recursively
    all_course_ids = set(c.id for c in target_courses)
    to_process = list(target_courses)

    while to_process:
        course = to_process.pop()
        for prereq_id in (course.prerequisites or []):
            if prereq_id not in all_course_ids:
                result = await db.execute(select(Course).where(Course.id == prereq_id))
                prereq = result.scalar_one_or_none()
                if prereq:
                    all_course_ids.add(prereq_id)
                    to_process.append(prereq)

    # Fetch all courses
    result = await db.execute(select(Course).where(Course.id.in_(all_course_ids)))
    all_courses = list(result.scalars().all())

    # Topological sort
    sorted_courses = topological_sort(all_courses)

    # Assign milestones
    milestones = assign_milestones(sorted_courses)

    # Estimate duration
    estimated_weeks = estimate_weeks(sorted_courses, hours_per_week)

    # Create learning path
    path = LearningPath(
        user_id=user_id,
        title=title,
        description=description,
        estimated_weeks=estimated_weeks,
        status="active",
    )
    db.add(path)
    await db.flush()  # Get path.id

    # Create path nodes
    for i, (course, milestone) in enumerate(zip(sorted_courses, milestones)):
        node = PathNode(
            path_id=path.id,
            course_id=course.id,
            order_index=i,
            milestone_type=milestone,
        )
        db.add(node)

    await db.commit()
    await db.refresh(path)

    # Load with nodes
    result = await db.execute(
        select(LearningPath).where(LearningPath.id == path.id)
    )
    return result.scalar_one()


async def get_learning_path(db: AsyncSession, path_id: UUID) -> Optional[LearningPath]:
    """Get learning path with nodes and courses."""
    result = await db.execute(
        select(LearningPath).where(LearningPath.id == path_id)
    )
    path = result.scalar_one_or_none()

    if path:
        # Load nodes with courses
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(LearningPath)
            .options(selectinload(LearningPath.nodes).selectinload(PathNode.course))
            .where(LearningPath.id == path_id)
        )
        path = result.scalar_one()

    return path


async def mark_node_complete(
    db: AsyncSession,
    path_id: UUID,
    node_id: UUID,
) -> Optional[PathNode]:
    """Mark a path node as completed."""
    from datetime import datetime

    result = await db.execute(
        select(PathNode).where(
            PathNode.id == node_id,
            PathNode.path_id == path_id
        )
    )
    node = result.scalar_one_or_none()

    if node and not node.is_completed:
        node.is_completed = True
        node.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(node)

    return node


async def get_next_recommendations(db: AsyncSession, path_id: UUID, limit: int = 3) -> List[Course]:
    """Get next recommended courses based on path progress."""
    path = await get_learning_path(db, path_id)
    if not path:
        return []

    # Find first incomplete node
    next_node = None
    for node in path.nodes:
        if not node.is_completed:
            next_node = node
            break

    if not next_node:
        return []  # Path complete

    # Return next few nodes' courses
    next_courses = []
    for node in path.nodes:
        if node.order_index >= next_node.order_index and not node.is_completed:
            next_courses.append(node.course)
            if len(next_courses) >= limit:
                break

    return next_courses


async def recalculate_path(db: AsyncSession, path_id: UUID) -> LearningPath:
    """Recalculate path after user feedback or completion."""
    # For now, just return the path - future enhancement could reorder based on progress
    path = await get_learning_path(db, path_id)
    return path