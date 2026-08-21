import { useQuery } from '@tanstack/react-query';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { LearningPath } from '../types';
import { cn, formatDate, getDifficultyColor, getMilestoneColor, getMilestoneIcon } from '../utils/helpers';
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Circle,
  Clock,
  BookOpen,
  Target,
  ArrowRight,
  RefreshCw,
  Download,
  Share2,
} from 'lucide-react';
import { useState } from 'react';

export function PathViewPage() {
  const { pathId } = useParams<{ pathId: string }>();
  const navigate = useNavigate();
  const [showCompleted, setShowCompleted] = useState(true);

  const { data: path, isLoading, error, refetch } = useQuery({
    queryKey: ['path', pathId],
    queryFn: () => api.getPath(pathId!),
    enabled: !!pathId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !path) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-medium text-gray-900 mb-2">Path not found</h2>
        <p className="text-gray-500 mb-6">The learning path you're looking for doesn't exist.</p>
        <Link to="/dashboard" className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const completedCount = path.nodes.filter(n => n.is_completed).length;
  const totalCount = path.nodes.length;
  const progressPercentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Group nodes by milestone
  const milestones = ['foundation', 'core', 'specialization', 'capstone'] as const;
  const groupedNodes = milestones.map(milestone => ({
    milestone,
    nodes: path.nodes.filter(n => n.milestone_type === milestone),
  })).filter(g => g.nodes.length > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">{path.title}</h1>
          <p className="text-gray-600 mt-1">{path.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn('badge', path.status === 'active' ? 'badge-primary' : 'badge-gray')}>
            {path.status}
          </span>
          <span className="badge badge-gray">{progressPercentage}% complete</span>
          <button
            onClick={() => refetch()}
            className="btn-secondary p-2"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button className="btn-secondary p-2" title="Download">
            <Download className="w-4 h-4" />
          </button>
          <button className="btn-secondary p-2" title="Share">
            <Share2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress Overview */}
      <div className="card p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="relative w-24 h-24">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="48"
                  cy="48"
                  r="40"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="8"
                />
                <circle
                  cx="48"
                  cy="48"
                  r="40"
                  fill="none"
                  stroke="#0ea5e9"
                  strokeWidth="8"
                  strokeDasharray={`${progressPercentage / 100 * 251.2} 251.2`}
                  strokeLinecap="round"
                  className="transition-all duration-500"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold text-gray-900">{progressPercentage}%</span>
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500">Overall Progress</p>
              <p className="text-2xl font-bold text-gray-900">
                {completedCount} of {totalCount} courses completed
              </p>
              {path.estimated_weeks && (
                <p className="text-sm text-gray-500 mt-1">
                  Estimated {path.estimated_weeks} weeks total
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{completedCount}</p>
              <p className="text-sm text-gray-500">Completed</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {totalCount - completedCount}
              </p>
              <p className="text-sm text-gray-500">Remaining</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {path.nodes.reduce((acc, n) => acc + (n.course?.duration_hours || 0), 0)}
              </p>
              <p className="text-sm text-gray-500">Total Hours</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-gray-700">Show completed courses</span>
        </label>
      </div>

      {/* Milestone Sections */}
      <div className="space-y-8">
        {groupedNodes.map(({ milestone, nodes }) => {
          const visibleNodes = showCompleted ? nodes : nodes.filter(n => !n.is_completed);
          if (visibleNodes.length === 0) return null;

          const milestoneCompleted = nodes.filter(n => n.is_completed).length;
          const milestoneTotal = nodes.length;
          const milestoneProgress = milestoneTotal > 0 ? Math.round((milestoneCompleted / milestoneTotal) * 100) : 0;

          return (
            <div key={milestone} className="card overflow-hidden">
              {/* Milestone Header */}
              <div className="bg-gray-50 border-b border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getMilestoneIcon(milestone)}</span>
                    <div>
                      <h3 className="font-semibold text-gray-900 capitalize">{milestone}</h3>
                      <p className="text-sm text-gray-500">
                        {milestoneCompleted}/{milestoneTotal} courses • {milestoneProgress}% complete
                      </p>
                    </div>
                  </div>
                  <div className="hidden md:flex items-center gap-4">
                    <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full transition-all duration-500', getMilestoneColor(milestone).replace('text-', 'bg-').replace('bg-', 'bg-'))}
                        style={{ width: `${milestoneProgress}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-600 w-12 text-right">
                      {milestoneProgress}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Courses in Milestone */}
              <div className="divide-y divide-gray-100">
                {visibleNodes.map((node, index) => (
                  <PathNodeDetail
                    key={node.id}
                    node={node}
                    index={index}
                    onComplete={async () => {
                      if (!node.is_completed) {
                        await api.markNodeComplete(path.id, node.id);
                        refetch();
                      }
                    }}
                  />
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* No active path */}
      {groupedNodes.length === 0 && (
        <div className="card p-12 text-center">
          <Target className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No courses in this path</h3>
          <p className="text-gray-500 mb-6">Generate a new learning path to get started</p>
          <Link to="/chat" className="btn-primary inline-flex">
            Create Learning Path
          </Link>
        </div>
      )}
    </div>
  );
}

function PathNodeDetail({
  node,
  index,
  onComplete,
}: {
  node: any;
  index: number;
  onComplete: () => Promise<void>;
}) {
  const isCompleted = node.is_completed;
  const course = node.course;

  return (
    <div className={cn('p-4 hover:bg-gray-50 transition-colors', isCompleted && 'bg-green-50/50')}>
      <div className="flex items-start gap-4">
        {/* Status Indicator */}
        <div className="flex flex-col items-center mt-1">
          <div
            className={cn(
              'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-medium border-2',
              isCompleted
                ? 'bg-green-500 border-green-500 text-white'
                : 'bg-white border-gray-300 text-gray-400'
            )}
            onClick={isCompleted ? undefined : onComplete}
            style={{ cursor: isCompleted ? 'default' : 'pointer' }}
          >
            {isCompleted ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <span>{index + 1}</span>
            )}
          </div>
          {!isCompleted && index < 4 && (
            <div className="w-0.5 h-8 bg-gray-200 mt-1" />
          )}
        </div>

        {/* Course Info */}
        <div className="flex-1 min-w-0">
          {course && (
            <Link to={`/courses/${course.id}`} className="block">
              <div className="flex items-start gap-3">
                <div className={cn('flex-shrink-0 w-14 h-14 rounded-lg', getDifficultyColor(course.difficulty).replace('text-', 'bg-').replace('bg-', 'bg-').replace('800', '100').replace('700', '100'))}>
                  <BookOpen className={cn('w-6 h-6', getDifficultyColor(course.difficulty))} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className={cn('font-medium truncate', isCompleted ? 'text-green-700' : 'text-gray-900')}>
                      {course.title}
                    </h4>
                    <span className={cn('badge', getMilestoneColor(node.milestone_type))}>
                      {node.milestone_type}
                    </span>
                    <span className={cn('badge', getDifficultyColor(course.difficulty))}>
                      {course.difficulty}
                    </span>
                    {course.rating && (
                      <span className="badge badge-gray flex items-center gap-1">
                        ★ {course.rating}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">{course.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {course.duration_hours}h
                    </span>
                    <span className="flex items-center gap-1">
                      <Target className="w-3.5 h-3.5" />
                      {course.skills_covered.slice(0, 3).join(', ')}
                      {course.skills_covered.length > 3 && '...'}
                    </span>
                  </div>
                </div>
              </div>
            </Link>
          )}

          {/* Prerequisites */}
          {course && course.prerequisites.length > 0 && (
            <div className="mt-3 ml-17 border-l-2 border-gray-200 pl-3">
              <p className="text-xs text-gray-500 mb-2">Prerequisites:</p>
              <div className="flex flex-wrap gap-1">
                {course.prerequisites.map((prereqId: string) => (
                  <span key={prereqId} className="badge badge-gray text-xs">
                    Course {prereqId.slice(0, 8)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col items-end gap-2">
          {isCompleted ? (
            <div className="text-right">
              <p className="text-sm font-medium text-green-700">Completed</p>
              {node.completed_at && (
                <p className="text-xs text-gray-500">
                  {formatDate(node.completed_at)}
                </p>
              )}
            </div>
          ) : (
            <button
              onClick={onComplete}
              className="btn-primary text-sm whitespace-nowrap"
              disabled={isCompleted}
            >
              Mark Complete
            </button>
          )}
          {course && (
            <Link
              to={`/courses/${course.id}`}
              className="btn-secondary text-sm whitespace-nowrap"
            >
              View Details
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}