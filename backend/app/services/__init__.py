from app.services.embeddings import (
    get_embedding,
    get_embeddings,
    embed_course,
    embed_profile,
    embed_courses_batch,
    cosine_similarity,
    build_course_text,
    build_profile_text,
)
from app.services.profiling import (
    analyze_profile_natural_language,
    get_or_create_profile,
    update_profile,
    add_completed_course,
    get_profile_with_user,
)
from app.services.recommendation import (
    get_recommendations,
    explain_recommendation,
)
from app.services.path_generator import (
    generate_learning_path,
    get_learning_path,
    mark_node_complete,
    get_next_recommendations,
    recalculate_path,
)
from app.services.ai_assistant import AIAssistant

__all__ = [
    "get_embedding",
    "get_embeddings",
    "embed_course",
    "embed_profile",
    "embed_courses_batch",
    "cosine_similarity",
    "build_course_text",
    "build_profile_text",
    "analyze_profile_natural_language",
    "get_or_create_profile",
    "update_profile",
    "add_completed_course",
    "get_profile_with_user",
    "get_recommendations",
    "explain_recommendation",
    "generate_learning_path",
    "get_learning_path",
    "mark_node_complete",
    "get_next_recommendations",
    "recalculate_path",
    "AIAssistant",
]