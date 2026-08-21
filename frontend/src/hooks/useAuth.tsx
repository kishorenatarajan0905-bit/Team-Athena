import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = api.loadToken();
      if (token) {
        try {
          // In a real app, you'd validate the token with a /me endpoint
          // For now, we'll decode the JWT to get user info
          const payload = JSON.parse(atob(token.split('.')[1]));
          setUser({
            id: payload.sub,
            email: '',
            name: 'User',
            created_at: new Date().toISOString(),
          });
        } catch {
          api.clearToken();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    await api.login({ email, password });
    // In a real app, fetch user profile here
    const token = api.loadToken();
    if (token) {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUser({
        id: payload.sub,
        email,
        name: 'User',
        created_at: new Date().toISOString(),
      });
    }
  };

  const register = async (email: string, password: string, name: string) => {
    await api.register({ email, password, name });
    const token = api.loadToken();
    if (token) {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUser({
        id: payload.sub,
        email,
        name,
        created_at: new Date().toISOString(),
      });
    }
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}