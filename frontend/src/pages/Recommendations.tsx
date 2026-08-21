import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { RecommendationItem, ExperienceLevel } from '../types';
import { cn, getDifficultyColor } from '../utils/helpers';
import {
  Filter,
  X,
  Star,
  Brain,
  ArrowRight,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const DOMAINS = [
  'Data Science',
  'Web Development',
  'DevOps',
  'Mobile Development',
  'Cybersecurity',
  'AI/ML',
];

const DIFFICULTIES: ExperienceLevel[] = ['beginner', 'intermediate', 'advanced'];

export function RecommendationsPage() {
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState<ExperienceLevel | null>(null);
  const [limit, setLimit] = useState(12);
  const queryClient = useQueryClient();

  const { data: recommendations, isLoading, error, refetch } = useQuery({
    queryKey: ['recommendations', selectedDomain, selectedDifficulty, limit],
    queryFn: () => api.getRecommendations({
      limit,
      domain: selectedDomain || undefined,
      difficulty: selectedDifficulty || undefined,
    }),
  });

  const explainMutation = useMutation({
    mutationFn: (courseId: string) => api.explainRecommendation(courseId),
  });

  const [explanations, setExplanations] = useState<Record<string, string>>({});

  const handleExplain = async (courseId: string) => {
    if (explanations[courseId]) return;
    try {
      const result = await explainMutation.mutateAsync(courseId);
      setExplanations(prev => ({ ...prev, [courseId]: result.explanation }));
    } catch (error) {
      console.error('Failed to get explanation:', error);
    }
  };

  const hasFilters = selectedDomain || selectedDifficulty;

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="card p-4 animate-pulse">
            <div className="h-32 bg-gray-200 rounded-lg mb-3" />
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Failed to load recommendations</p>
        <button onClick={() => refetch()} className="btn-primary mt-4">Retry</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recommendations</h1>
          <p className="text-gray-600 mt-1">
            Personalized course suggestions based on your profile and goals
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="input py-2 px-3 text-sm"
          >
            <option value={6}>Show 6</option>
            <option value={12}>Show 12</option>
            <option value={20}>Show 20</option>
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {DOMAINS.map((domain) => (
              <button
                key={domain}
                onClick={() => setSelectedDomain(selectedDomain === domain ? null : domain)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  selectedDomain === domain
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
              >
                {domain}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {DIFFICULTIES.map((difficulty) => (
              <button
                key={difficulty}
                onClick={() => setSelectedDifficulty(selectedDifficulty === difficulty ? null : difficulty)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors',
                  getDifficultyColor(difficulty),
                  selectedDifficulty === difficulty
                    ? 'ring-2 ring-offset-2'
                    : 'hover:opacity-80'
                )}
              >
                {difficulty}
              </button>
            ))}
          </div>

          {hasFilters && (
            <button
              onClick={() => {
                setSelectedDomain(null);
                setSelectedDifficulty(null);
              }}
              className="btn-ghost text-sm"
            >
              <X className="w-4 h-4 mr-1" />
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Recommendations Grid */}
      {recommendations?.recommendations.length === 0 ? (
        <div className="card p-12 text-center">
          <Brain className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No recommendations found</h3>
          <p className="text-gray-500 mb-6">
            Try adjusting your filters or complete your profile for better suggestions.
          </p>
          <Link to="/chat" className="btn-primary inline-flex">
            Chat with AI Coach
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {recommendations?.recommendations.map((rec) => (
            <RecommendationCard
              key={rec.course.id}
              recommendation={rec}
              explanation={explanations[rec.course.id]}
              onExplain={() => handleExplain(rec.course.id)}
            />
          ))}
        </div>
      )}

      {/* Load More */}
      {recommendations && recommendations.recommendations.length >= limit && (
        <div className="text-center">
          <button
            onClick={() => setLimit(limit + 10)}
            className="btn-secondary"
          >
            Load More
          </button>
        </div>
      )}
    </div>
  );
}

function RecommendationCard({
  recommendation,
  explanation,
  onExplain,
}: {
  recommendation: RecommendationItem;
  explanation: string | undefined;
  onExplain: () => void;
}) {
  const { course, score, reason } = recommendation;
  const matchPercentage = Math.round(score * 100);

  return (
    <Link to={`/courses/${course.id}`} className="block card-hover h-full flex flex-col">
      <div className="p-5 flex-1">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
              <Star className="w-5 h-5 text-primary-600" />
            </div>
            <span className="text-sm font-medium text-gray-700">{matchPercentage}% Match</span>
          </div>
          <span className={cn('badge', getDifficultyColor(course.difficulty))}>
            {course.difficulty}
          </span>
        </div>

        <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">{course.title}</h3>
        <p className="text-sm text-gray-500 mb-3 line-clamp-3">{course.description}</p>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {course.skills_covered.slice(0, 4).map((skill) => (
            <span key={skill} className="badge badge-gray text-xs">{skill}</span>
          ))}
          {course.skills_covered.length > 4 && (
            <span className="badge badge-gray text-xs">+{course.skills_covered.length - 4} more</span>
          )}
        </div>

        <div className="flex items-center gap-3 text-sm text-gray-500 mb-4">
          <span className="flex items-center gap-1">
            <Star className="w-3.5 h-3.5 text-yellow-500" />
            {course.rating ? course.rating.toFixed(1) : 'N/A'}
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {course.duration_hours}h
          </span>
        </div>

        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <p className="text-sm text-gray-600">
            <strong className="text-gray-900">Why this course:</strong> {reason}
          </p>
        </div>

        {explanation && (
          <div className="bg-primary-50 border border-primary-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-primary-800">
              <strong>AI Explanation:</strong> {explanation}
            </p>
          </div>
        )}
      </div>

      <div className="p-5 border-t border-gray-100 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onExplain();
              }}
              className="btn-ghost text-sm p-2"
              title="Get detailed explanation"
            >
              <Brain className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">{course.domain}</span>
            <ArrowRight className="w-4 h-4 text-gray-400" />
          </div>
        </div>
      </div>
    </Link>
  );
}