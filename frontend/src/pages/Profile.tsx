import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { LearnerProfile, ExperienceLevel } from '../types';
import { cn, getDifficultyColor } from '../utils/helpers';
import {
  User,
  Target,
  Clock,
  BookOpen,
  Brain,
  Save,
  Loader2,
  CheckCircle2,
  Edit2,
  X,
  Plus,
  Trash2,
} from 'lucide-react';

const EXPERIENCE_LEVELS: { value: ExperienceLevel; label: string; description: string }[] = [
  { value: 'beginner', label: 'Beginner', description: 'New to the field, learning fundamentals' },
  { value: 'intermediate', label: 'Intermediate', description: 'Some experience, building practical skills' },
  { value: 'advanced', label: 'Advanced', description: 'Experienced, seeking specialization' },
];

const LEARNING_STYLES = [
  'hands-on',
  'theoretical',
  'project-based',
  'video-based',
  'reading',
  'interactive',
];

export function ProfilePage() {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<LearnerProfile>>({});

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<LearnerProfile>) => api.updateProfile(data),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(['profile'], updatedProfile);
      setIsEditing(false);
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (goals: string) => api.analyzeProfile(goals),
  });

  const [goalsInput, setGoalsInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyzeGoals = async () => {
    if (!goalsInput.trim()) return;
    setIsAnalyzing(true);
    try {
      const analysis = await analyzeMutation.mutateAsync(goalsInput);
      setFormData(prev => ({
        ...prev,
        interests: analysis.interests,
        experience_level: analysis.experience_level,
        goals: analysis.goals,
        target_role: analysis.target_role,
        time_commitment_hours: analysis.time_commitment_hours,
        learning_style: analysis.learning_style,
      }));
    } catch (error) {
      console.error('Failed to analyze goals:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Failed to load profile</p>
      </div>
    );
  }

  // Initialize form data
  if (Object.keys(formData).length === 0) {
    setFormData({
      interests: profile.interests,
      experience_level: profile.experience_level,
      goals: profile.goals,
      target_role: profile.target_role,
      time_commitment_hours: profile.time_commitment_hours,
      learning_style: profile.learning_style,
    });
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const handleCancel = () => {
    setFormData({
      interests: profile.interests,
      experience_level: profile.experience_level,
      goals: profile.goals,
      target_role: profile.target_role,
      time_commitment_hours: profile.time_commitment_hours,
      learning_style: profile.learning_style,
    });
    setIsEditing(false);
  };

  const addInterest = (e: React.FormEvent<HTMLInputElement>) => {
    e.preventDefault();
    const input = e.currentTarget;
    const value = input.value.trim();
    if (value && !formData.interests?.includes(value)) {
      setFormData(prev => ({
        ...prev,
        interests: [...(prev.interests || []), value],
      }));
      input.value = '';
    }
  };

  const removeInterest = (interest: string) => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests?.filter(i => i !== interest) || [],
    }));
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
          <p className="text-gray-600 mt-1">Manage your learning preferences and goals</p>
        </div>
        <button
          onClick={() => setIsEditing(!isEditing)}
          className={cn('btn', isEditing ? 'btn-secondary' : 'btn-primary')}
        >
          {isEditing ? (
            <>
              <X className="w-4 h-4 mr-2" />
              Cancel
            </>
          ) : (
            <>
              <Edit2 className="w-4 h-4 mr-2" />
              Edit Profile
            </>
          )}
        </button>
      </div>

      {/* AI Goal Analysis */}
      <div className="card p-6 border-accent-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-accent-100 flex items-center justify-center">
            <Brain className="w-5 h-5 text-accent-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">AI Goal Analysis</h3>
            <p className="text-sm text-gray-500">Describe your goals in natural language</p>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={goalsInput}
            onChange={(e) => setGoalsInput(e.target.value)}
            placeholder="e.g., I want to become a machine learning engineer..."
            className="flex-1 input"
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyzeGoals()}
          />
          <button
            onClick={handleAnalyzeGoals}
            disabled={isAnalyzing || !goalsInput.trim()}
            className="btn-accent"
          >
            {isAnalyzing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Brain className="w-4 h-4 mr-1" />
                Analyze
              </>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          The AI will extract your interests, experience level, target role, and learning preferences.
        </p>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-primary-600" />
            Basic Information
          </h2>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Target Role</label>
              <input
                type="text"
                value={formData.target_role || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, target_role: e.target.value }))}
                placeholder="e.g., Machine Learning Engineer"
                className="input"
                disabled={!isEditing}
              />
            </div>
            
            <div>
              <label className="label">Experience Level</label>
              <select
                value={formData.experience_level || 'beginner'}
                onChange={(e) => setFormData(prev => ({ ...prev, experience_level: e.target.value as ExperienceLevel }))}
                className="input"
                disabled={!isEditing}
              >
                {EXPERIENCE_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Weekly Time Commitment (hours)</label>
              <input
                type="number"
                value={formData.time_commitment_hours || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, time_commitment_hours: Number(e.target.value) || null }))}
                placeholder="15"
                min="1"
                max="40"
                className="input"
                disabled={!isEditing}
              />
            </div>

            <div>
              <label className="label">Learning Style</label>
              <select
                value={formData.learning_style || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, learning_style: e.target.value || null }))}
                className="input"
                disabled={!isEditing}
              >
                <option value="">Select a style</option>
                {LEARNING_STYLES.map((style) => (
                  <option key={style} value={style}>
                    {style.charAt(0).toUpperCase() + style.slice(1).replace('-', ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Goals */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary-600" />
            Learning Goals
          </h2>
          
          <textarea
            value={formData.goals || ''}
            onChange={(e) => setFormData(prev => ({ ...prev, goals: e.target.value }))}
            placeholder="Describe your learning objectives..."
            rows={4}
            className="input resize-none"
            disabled={!isEditing}
          />
          <p className="text-xs text-gray-500 mt-1">
            What do you want to achieve? Be specific about the skills you want to develop.
          </p>
        </div>

        {/* Interests */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary-600" />
            Interests & Topics
          </h2>
          
          <div className="flex flex-wrap gap-2 mb-3">
            {formData.interests?.map((interest) => (
              <span key={interest} className="flex items-center gap-1 badge badge-primary">
                {interest}
                <button
                  type="button"
                  onClick={() => removeInterest(interest)}
                  className="hover:text-primary-700"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
          
          <form onSubmit={addInterest} className="flex gap-2">
            <input
              type="text"
              placeholder="Add interest (e.g., Python, React, Kubernetes)..."
              className="flex-1 input"
              disabled={!isEditing}
            />
            <button type="submit" disabled={!isEditing} className="btn-primary">
              <Plus className="w-4 h-4" />
            </button>
          </form>
        </div>

        {/* Completed Courses Count */}
        <div className="card p-6 bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-primary-100 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Completed Courses</p>
              <p className="text-2xl font-bold text-gray-900">{profile.completed_course_ids?.length || 0}</p>
            </div>
          </div>
        </div>

        {/* Save/Cancel Buttons */}
        {isEditing && (
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={handleCancel} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={updateMutation.isPending} className="btn-primary">
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        )}
      </form>

      {/* Profile Summary (read-only when not editing) */}
      {!isEditing && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile Summary</h2>
          <dl className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-gray-500">Target Role</dt>
                <dd className="text-gray-900 mt-1">{profile.target_role || 'Not set'}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Experience Level</dt>
                <dd className={cn('mt-1 badge capitalize', getDifficultyColor(profile.experience_level))}>
                  {profile.experience_level}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Weekly Hours</dt>
                <dd className="text-gray-900 mt-1">{profile.time_commitment_hours || 'Not set'} hours</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Learning Style</dt>
                <dd className="text-gray-900 mt-1 capitalize">{profile.learning_style || 'Not set'}</dd>
              </div>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Goals</dt>
              <dd className="text-gray-900 mt-1 whitespace-pre-wrap">{profile.goals || 'Not set'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Interests</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {profile.interests?.map((interest) => (
                  <span key={interest} className="badge badge-gray">{interest}</span>
                ))}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}