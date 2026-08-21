import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type { User, Course, LearningPath, ChatRequest, ChatResponse, RecommendationResponse, DashboardResponse, ProfileAnalysisResponse, LearnerProfile, PathNode } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  loadToken() {
    const token = localStorage.getItem('token');
    if (token) {
      this.token = token;
    }
    return token;
  }

  // Auth
  async register(data: { email: string; password: string; name: string }) {
    const response = await this.client.post<{ access_token: string }>('/auth/register', data);
    this.setToken(response.data.access_token);
    return response.data;
  }

  async login(data: { email: string; password: string }) {
    const response = await this.client.post<{ access_token: string }>('/auth/login', data);
    this.setToken(response.data.access_token);
    return response.data;
  }

  logout() {
    this.clearToken();
  }

  // Profile
  async getProfile(): Promise<LearnerProfile> {
    const response = await this.client.get<LearnerProfile>('/profile');
    return response.data;
  }

  async updateProfile(data: Partial<LearnerProfile>): Promise<LearnerProfile> {
    const response = await this.client.put<LearnerProfile>('/profile', data);
    return response.data;
  }

  async analyzeProfile(goals: string): Promise<ProfileAnalysisResponse> {
    const response = await this.client.post<ProfileAnalysisResponse>('/profile/analyze', {
      natural_language_goals: goals,
    });
    return response.data;
  }

  // Recommendations
  async getRecommendations(params?: {
    limit?: number;
    domain?: string;
    difficulty?: string;
  }): Promise<RecommendationResponse> {
    const response = await this.client.get<RecommendationResponse>('/recommendations', { params });
    return response.data;
  }

  async explainRecommendation(courseId: string): Promise<{ explanation: string }> {
    const response = await this.client.get<{ explanation: string }>(`/recommendations/${courseId}/explain`);
    return response.data;
  }

  // Learning Paths
  async generatePath(data: {
    title: string;
    description: string;
    target_course_ids?: string[];
    hours_per_week?: number;
  }): Promise<LearningPath> {
    const response = await this.client.post<LearningPath>('/paths/generate', data);
    return response.data;
  }

  async getPaths(): Promise<LearningPath[]> {
    const response = await this.client.get<LearningPath[]>('/paths');
    return response.data;
  }

  async getPath(pathId: string): Promise<LearningPath> {
    const response = await this.client.get<LearningPath>(`/paths/${pathId}`);
    return response.data;
  }

  async markNodeComplete(pathId: string, nodeId: string): Promise<{ success: boolean; message: string }> {
    const response = await this.client.patch<{ success: boolean; message: string }>(
      `/paths/${pathId}/nodes/${nodeId}`,
      { is_completed: true }
    );
    return response.data;
  }

  async getNextActions(pathId: string, limit = 3): Promise<Course[]> {
    const response = await this.client.get<Course[]>(`/paths/${pathId}/next`, { params: { limit } });
    return response.data;
  }

  // Chat
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', request);
    return response.data;
  }

  // Dashboard
  async getDashboard(): Promise<DashboardResponse> {
    const response = await this.client.get<DashboardResponse>('/dashboard');
    return response.data;
  }
}

export const api = new ApiClient();