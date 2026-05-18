import { useCallback, useState } from 'react';

const PROFILE_KEY = 'iching_profile_v1';

export interface UserProfile {
  name: string;
  age: number;
}

/** Profile persisted to localStorage only — no auth or Supabase dependency. */
export function useProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(() => {
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      return raw ? (JSON.parse(raw) as UserProfile) : null;
    } catch {
      return null;
    }
  });

  const saveProfile = useCallback((data: UserProfile) => {
    if (!Number.isFinite(data.age) || data.age < 1 || data.age > 120) {
      throw new Error(`Invalid age: ${data.age}`);
    }
    localStorage.setItem(PROFILE_KEY, JSON.stringify(data));
    setProfile(data);
  }, []);

  const clearProfile = useCallback(() => {
    localStorage.removeItem(PROFILE_KEY);
    setProfile(null);
  }, []);

  return { profile, saveProfile, clearProfile };
}
