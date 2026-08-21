import structlog
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.nvidia_client import nvidia_client
from app.models import User, LearnerProfile, Course, LearningPath, PathNode, Conversation
from app.schemas import (
    ChatMessage, ChatRequest, ChatResponse,
    CourseResponse, LearningPathResponse, PathNodeResponse
)
from app.services.profiling import get_or_create_profile, analyze_profile_natural_language
from app.services.recommendation import get_recommendations, explain_recommendation
from app.services.path_generator import generate_learning_path, get_learning_path, get_next_recommendations
from app.services.embeddings import embed_profile

logger = structlog.get_logger()


AI_ASSISTANT_SYSTEM_PROMPT = """You are an expert AI Learning Coach for the Personalized Learning Path Recommender.

Your role is to help learners:
1. Understand their learning goals and create a structured profile
2. Get personalized course recommendations with clear explanations
3. Generate and navigate structured learning paths with milestones
4. Track progress and adapt their learning journey
5. Answer questions about courses, skills, and career paths

You have access to tools to:
- Analyze natural language goals into structured profiles
- Get learner profiles and progress
- Generate course recommendations with reasoning
- Create and manage learning paths
- Explain why specific courses were recommended

Always be encouraging, specific, and actionable. When making recommendations, explain WHY.
When users ask questions, use the appropriate tools to get accurate, personalized information.

Key principles:
- Personalize everything to the learner's profile
- Explain the reasoning behind recommendations
- Break complex goals into manageable milestones
- Adapt suggestions based on progress and feedback
- Be conversational but structured"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_goals",
            "description": "Analyze natural language learning goals into a structured profile",
            "parameters": {
                "type": "object",
                "properties": {
                    "natural_language_goals": {"type": "string", "description": "User's learning goals in their own words"},
                },
                "required": ["natural_language_goals"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learner_profile",
            "description": "Get the current learner's profile including interests, experience level, goals, and completed courses",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "Get personalized course recommendations for the learner",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                    "domain": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_recommendation",
            "description": "Explain why a specific course was recommended for the learner",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {"type": "string", "description": "UUID of the course"},
                },
                "required": ["course_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_learning_path",
            "description": "Generate a structured learning path with milestones for the learner",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "target_course_ids": {"type": "array", "items": {"type": "string"}},
                    "hours_per_week": {"type": "integer", "default": 10},
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learning_path",
            "description": "Get the learner's current learning path with all nodes and progress",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_actions",
            "description": "Get the next recommended courses to take based on current path progress",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 3},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_course_complete",
            "description": "Mark a course as completed in the learning path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_id": {"type": "string"},
                    "node_id": {"type": "string"},
                },
                "required": ["path_id", "node_id"],
            },
        },
    },
]


class AIAssistant:
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id

    async def _get_user(self) -> User:
        result = await self.db.execute(select(User).where(User.id == self.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        return user

    async def _get_profile(self) -> LearnerProfile:
        return await get_or_create_profile(self.db, self.user_id)

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool call and return the result."""
        try:
            if tool_name == "analyze_goals":
                result = await analyze_profile_natural_language(arguments["natural_language_goals"])
                return result.model_dump()

            elif tool_name == "get_learner_profile":
                profile = await self._get_profile()
                return {
                    "interests": profile.interests,
                    "experience_level": profile.experience_level.value,
                    "goals": profile.goals,
                    "target_role": profile.target_role,
                    "time_commitment_hours": profile.time_commitment_hours,
                    "learning_style": profile.learning_style,
                    "completed_course_count": len(profile.completed_course_ids or []),
                }

            elif tool_name == "get_recommendations":
                rec_response = await get_recommendations(
                    self.db,
                    self.user_id,
                    limit=arguments.get("limit", 10),
                    domain=arguments.get("domain"),
                    difficulty=arguments.get("difficulty"),
                )
                return {
                    "recommendations": [
                        {
                            "course": r.course.model_dump(),
                            "score": r.score,
                            "reason": r.reason,
                        }
                        for r in rec_response.recommendations
                    ]
                }

            elif tool_name == "explain_recommendation":
                explanation = await explain_recommendation(
                    self.db, self.user_id, UUID(arguments["course_id"])
                )
                return {"explanation": explanation}

            elif tool_name == "generate_learning_path":
                target_ids = [UUID(id) for id in arguments.get("target_course_ids", [])] if arguments.get("target_course_ids") else None
                path = await generate_learning_path(
                    self.db,
                    self.user_id,
                    arguments["title"],
                    arguments["description"],
                    target_ids,
                    arguments.get("hours_per_week", 10),
                )
                # Load with nodes
                full_path = await get_learning_path(self.db, path.id)
                return {
                    "path_id": str(full_path.id),
                    "title": full_path.title,
                    "description": full_path.description,
                    "estimated_weeks": full_path.estimated_weeks,
                    "nodes": [
                        {
                            "id": str(node.id),
                            "order_index": node.order_index,
                            "milestone_type": node.milestone_type.value,
                            "is_completed": node.is_completed,
                            "course": CourseResponse.model_validate(node.course).model_dump() if node.course else None,
                        }
                        for node in full_path.nodes
                    ],
                }

            elif tool_name == "get_learning_path":
                path = await get_learning_path(self.db, UUID(arguments["path_id"]))
                if not path:
                    return {"error": "Path not found"}
                return {
                    "path_id": str(path.id),
                    "title": path.title,
                    "description": path.description,
                    "estimated_weeks": path.estimated_weeks,
                    "status": path.status,
                    "nodes": [
                        {
                            "id": str(node.id),
                            "order_index": node.order_index,
                            "milestone_type": node.milestone_type.value,
                            "is_completed": node.is_completed,
                            "completed_at": node.completed_at.isoformat() if node.completed_at else None,
                            "course": CourseResponse.model_validate(node.course).model_dump() if node.course else None,
                        }
                        for node in path.nodes
                    ],
                }

            elif tool_name == "get_next_actions":
                courses = await get_next_recommendations(self.db, UUID(arguments["path_id"]), arguments.get("limit", 3))
                return {
                    "next_courses": [CourseResponse.model_validate(c).model_dump() for c in courses]
                }

            elif tool_name == "mark_course_complete":
                node = await mark_node_complete(self.db, UUID(arguments["path_id"]), UUID(arguments["node_id"]))
                if node:
                    # Also update profile
                    from app.services.profiling import add_completed_course
                    if node.course:
                        await add_completed_course(self.db, self.user_id, node.course_id)
                    return {"success": True, "message": f"Marked {node.course.title if node.course else 'course'} as complete"}
                return {"success": False, "message": "Node not found or already completed"}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error("tool_call_failed", tool=tool_name, error=str(e))
            return {"error": str(e)}

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Process a chat message and return response."""
        # Get or create conversation
        conversation = None
        if request.conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == request.conversation_id)
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(user_id=self.user_id, messages=[])
            self.db.add(conversation)
            await self.db.flush()

        # Add user message
        conversation.messages.append({"role": "user", "content": request.message})

        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": AI_ASSISTANT_SYSTEM_PROMPT},
        ]
        # Include recent conversation history (last 10 messages)
        for msg in conversation.messages[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Call LLM with tools
        response = await nvidia_client.chat_completion(
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.4,
        )

        message = response.choices[0].message
        tool_calls = []

        # Handle tool calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                result = await self.handle_tool_call(tool_name, args)

                tool_calls.append({
                    "name": tool_name,
                    "arguments": args,
                    "result": result,
                })

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

            # Get final response after tool calls
            final_response = await nvidia_client.chat_completion(
                messages=messages,
                tools=TOOLS,
                tool_choice="none",
                temperature=0.4,
            )
            assistant_message = final_response.choices[0].message.content
        else:
            assistant_message = message.content

        # Add assistant message to conversation
        conversation.messages.append({"role": "assistant", "content": assistant_message})
        await self.db.commit()

        return ChatResponse(
            message=assistant_message,
            conversation_id=conversation.id,
            tool_calls=tool_calls if tool_calls else None,
        )


async def mark_node_complete(db: AsyncSession, path_id: UUID, node_id: UUID):
    from app.services.path_generator import mark_node_complete as mark_complete
    return await mark_complete(db, path_id, node_id)