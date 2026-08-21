import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { DashboardResponse } from '../types';
import { cn, formatDate, getDifficultyColor, getMilestoneColor, getMilestoneIcon } from '../utils/helpers';
import {
  BookOpen,
  Target,
  Award,
  Clock,
  TrendingUp,
  Brain,
  ArrowRight,
  CheckCircle2,
  Circle,
  AlertCircle,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
} from 'recharts';

const COLORS = ['#0ea5e9', '#d946ef', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899'];

export function DashboardPage() {
  const { data: dashboard, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.getDashboard(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-gray-600">Failed to load dashboard</p>
      </div>
    );
  }

  if (!dashboard) return null;

  const { profile, active_path, skill_progress, milestones, next_actions, stats } = dashboard;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Welcome back, {dashboard.user.name}! Here's your learning progress overview.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Completed Courses"
          value={stats.completed_courses}
          icon={CheckCircle2}
          color="text-green-600"
          bgColor="bg-green-50"
        />
        <StatCard
          title="In Progress"
          value={stats.in_progress_courses}
          icon={Clock}
          color="text-blue-600"
          bgColor="bg-blue-50"
        />
        <StatCard
          title="Learning Paths"
          value={stats.total_paths}
          icon={Route}
          color="text-purple-600"
          bgColor="bg-purple-50"
        />
        <StatCard
          title="Estimated Weeks"
          value={stats.active_path_weeks}
          icon={Clock}
          color="text-orange-600"
          bgColor="bg-orange-50"
        />
      </div>

      {/* Active Path & Skill Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Learning Path */}
        <div className="lg:col-span-2 space-y-6">
          {active_path ? (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{active_path.title}</h2>
                  <p className="text-sm text-gray-500 mt-1">{active_path.description}</p>
                </div>
                <span className={cn('badge', active_path.status === 'active' ? 'badge-primary' : 'badge-gray')}>
                  {active_path.status}
                </span>
              </div>

              {/* Milestone Progress */}
              <div className="card p-4">
                <h3 className="font-medium text-gray-900 mb-4">Milestone Progress</h3>
                <div className="space-y-4">
                  {milestones.map((milestone) => (
                    <MilestoneProgressBar
                      key={milestone.milestone_type}
                      milestone={milestone}
                    />
                  ))}
                </div>
              </div>

              {/* Path Nodes */}
              <div className="card p-4">
                <h3 className="font-medium text-gray-900 mb-4">Your Learning Path</h3>
                <div className="space-y-3">
                  {active_path.nodes.map((node, index) => (
                    <PathNodeCard
                      key={node.id}
                      node={node}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            </>
          ) : (
            <EmptyState
              icon={Route}
              title="No active learning path"
              description="Create your first learning path to get started"
              actionLabel="Create Path"
              actionHref="/chat"
            />
          )}
        </div>

        {/* Skill Progress */}
        <div className="space-y-6">
          <div className="card p-4">
            <h3 className="font-medium text-gray-900 mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-primary-600" />
              Skill Development
            </h3>
            {skill_progress.length > 0 ? (
              <div className="space-y-4">
                {skill_progress.slice(0, 8).map((skill) => (
                  <SkillProgressBar key={skill.skill} skill={skill} />
                ))}
                {skill_progress.length > 8 && (
                  <p className="text-sm text-gray-500 text-center">
                    +{skill_progress.length - 8} more skills
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                Complete courses to track skill progress
              </p>
            )}
          </div>

          {/* Skill Distribution Chart */}
          {skill_progress.length > 0 && (
            <div className="card p-4">
              <h3 className="font-medium text-gray-900 mb-4">Skill Distribution</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={skill_progress.slice(0, 6).map((s, i) => ({
                        name: s.skill.length > 12 ? s.skill.slice(0, 12) + '...' : s.skill,
                        value: s.level * 100,
                        color: COLORS[i % COLORS.length],
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                      nameKey="name"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {skill_progress.slice(0, 6).map((_, i) => (
                        <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Next Actions */}
          <div className="card p-4">
            <h3 className="font-medium text-gray-900 mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-accent-600" />
              Recommended Next Steps
            </h3>
            {next_actions.length > 0 ? (
              <div className="space-y-3">
                {next_actions.slice(0, 3).map((course) => (
                  <NextActionCard key={course.id} course={course} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                Generate a learning path to see recommendations
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Stats Chart */}
      <div className="card p-6">
        <h3 className="font-medium text-gray-900 mb-4">Learning Activity</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={[
                { name: 'Mon', courses: 2, hours: 3 },
                { name: 'Tue', courses: 1, hours: 2 },
                { name: 'Wed', courses: 3, hours: 4 },
                { name: 'Thu', courses: 2, hours: 3 },
                { name: 'Fri', courses: 1, hours: 2 },
                { name: 'Sat', courses: 2, hours: 5 },
                { name: 'Sun', courses: 1, hours: 3 },
              ]}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
              <Tooltip
                formatter={(value: number, name: string) => [
                  value,
                  name === 'courses' ? 'Courses completed' : 'Hours studied',
                ]}
              />
              <Legend />
              <Bar dataKey="courses" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Courses" />
              <Bar dataKey="hours" fill="#d946ef" radius={[4, 4, 0, 0]} name="Hours" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  bgColor,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}) {
  return (
    <div className={cn('card p-5', bgColor)}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', bgColor.replace('bg-', 'bg-'))}>
          <Icon className={cn('w-6 h-6', color)} />
        </div>
      </div>
    </div>
  );
}

function MilestoneProgressBar({
  milestone,
}: {
  milestone: {
    milestone_type: string;
    completed: number;
    total: number;
    courses: any[];
  };
}) {
  const percentage = milestone.total > 0 ? (milestone.completed / milestone.total) * 100 : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getMilestoneIcon(milestone.milestone_type)}</span>
          <span className="font-medium capitalize">{milestone.milestone_type}</span>
          <span className={cn('badge badge-gray')}>
            {milestone.completed}/{milestone.total}
          </span>
        </div>
        <span className="text-sm font-medium text-gray-600">{percentage.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', getMilestoneColor(milestone.milestone_type).replace('text-', 'bg-').replace('bg-', 'bg-'))}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function PathNodeCard({ node, index }: { node: any; index: number }) {
  const isCompleted = node.is_completed;
  const course = node.course;

  return (
    <div className={cn('flex items-center gap-4 p-3 rounded-lg transition-colors', isCompleted ? 'bg-green-50' : 'hover:bg-gray-50')}>
      <div className={cn(
        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-medium',
        isCompleted
          ? 'bg-green-500 text-white'
          : 'bg-gray-200 text-gray-600'
      )}>
        {isCompleted ? (
          <CheckCircle2 className="w-5 h-5" />
        ) : (
          <span>{index + 1}</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className={cn('font-medium truncate', isCompleted ? 'text-green-700' : 'text-gray-900')}>
            {course?.title || 'Unknown Course'}
          </h4>
          <span className={cn('badge', getMilestoneColor(node.milestone_type))}>
            {node.milestone_type}
          </span>
          <span className={cn('badge', getDifficultyColor(course?.difficulty || ''))}>
            {course?.difficulty || ''}
          </span>
        </div>
        {course && (
          <p className="text-sm text-gray-500 mt-1 truncate">{course.description}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        {course && (
          <span className="text-sm text-gray-500">{course.duration_hours}h</span>
        )}
        {isCompleted && node.completed_at && (
          <span className="text-xs text-gray-400">
            Completed {formatDate(node.completed_at)}
          </span>
        )}
      </div>
    </div>
  );
}

function SkillProgressBar({ skill }: { skill: any }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-900 truncate pr-2">{skill.skill}</span>
        <span className="text-sm text-gray-500">
          {(skill.level * 100).toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary-500 rounded-full transition-all duration-500"
          style={{ width: `${skill.level * 100}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">
        {skill.courses_completed}/{skill.courses_total} courses
      </p>
    </div>
  );
}

function NextActionCard({ course }: { course: any }) {
  return (
    <Link to={`/courses/${course.id}`} className="block">
      <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
        <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0">
          <BookOpen className="w-5 h-5 text-primary-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 truncate">{course.title}</h4>
          <div className="flex items-center gap-2 mt-1">
            <span className={cn('badge badge-gray text-xs')}>{course.difficulty}</span>
            <span className="text-xs text-gray-500">{course.duration_hours}h</span>
            {course.rating && (
              <span className="text-xs text-yellow-600 flex items-center gap-0.5">
                ★ {course.rating}
              </span>
            )}
          </div>
        </div>
        <ArrowRight className="w-5 h-5 text-gray-400" />
      </div>
    </Link>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  actionLabel: string;
  actionHref: string;
}) {
  return (
    <div className="card p-8 text-center">
      <Icon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6">{description}</p>
      <a href={actionHref} className="btn-primary inline-flex">
        {actionLabel}
      </a>
    </div>
  );
}

// Simple Legend component for recharts
function Legend() {
  return null;
}