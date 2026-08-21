export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type MilestoneType = 'foundation' | 'core' | 'specialization' | 'capstone';

export interface LearnerProfile {
  user_id: string;
  interests: string[];
  experience_level: ExperienceLevel;
  goals: string;
  target_role: string | null;
  time_commitment_hours: number | null;
  learning_style: string | null;
  completed_course_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Course {
  id: string;
  title: string;
  description: string;
  domain: string;
  difficulty: ExperienceLevel;
  duration_hours: number;
  prerequisites: string[];
  skills_covered: string[];
  provider: string | null;
  url: string | null;
  rating: number | null;
  created_at: string;
  updated_at: string;
}

export interface PathNode {
  id: string;
  path_id: string;
  course_id: string;
  order_index: number;
  milestone_type: MilestoneType;
  is_completed: boolean;
  completed_at: string | null;
  notes: string | null;
  course?: Course;
  created_at: string;
}

export interface LearningPath {
  id: string;
  user_id: string;
  title: string;
  description: string;
  status: string;
  estimated_weeks: number | null;
  nodes: PathNode[];
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: any[];
  tool_call_id?: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
  tool_calls?: any[];
}

export interface RecommendationItem {
  course: Course;
  score: number;
  reason: string;
}

export interface RecommendationResponse {
  recommendations: RecommendationItem[];
}

export interface SkillProgress {
  skill: string;
  level: number;
  courses_completed: number;
  courses_total: number;
}

export interface MilestoneProgress {
  milestone_type: MilestoneType;
  completed: number;
  total: number;
  courses: Course[];
}

export interface DashboardResponse {
  user: User;
  profile: LearnerProfile;
  active_path: LearningPath | null;
  skill_progress: SkillProgress[];
  milestones: MilestoneProgress[];
  next_actions: Course[];
  stats: {
    completed_courses: number;
    in_progress_courses: number;
    total_paths: number;
    active_path_weeks: number;
  };
}

export interface ProfileAnalysisResponse {
  interests: string[];
  experience_level: ExperienceLevel;
  goals: string;
  target_role: string | null;
  time_commitment_hours: number | null;
  learning_style: string | null;
  suggested_domains: string[];
}