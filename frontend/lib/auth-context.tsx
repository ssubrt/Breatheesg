'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { UserProfile } from './types';
import { get, logout as logoutAPI } from './api';

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  refetch: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      const response = await get<{ count: number; results: UserProfile[] } | UserProfile>('/users/');

      if ('error' in response || 'detail' in response) {
        setUser(null);
      } else if ('results' in response) {
        // Paginated list response — pick the first result
        setUser(response.results[0] ?? null);
      } else {
        // Direct object response — already ruled out APIError and paginated shape
        setUser(response as UserProfile);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const logout = () => {
    setUser(null);
    logoutAPI();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        logout,
        refetch: fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
