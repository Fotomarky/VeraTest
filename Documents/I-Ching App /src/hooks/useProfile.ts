import { useState } from 'react';

const PROFILE_KEY = 'iching_profile_v1';

export interface UserProfile {
  name: string;
  age: number;
}

export function useProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(() => {
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      return raw ? (JSON.parse(raw) as UserProfile) : null;
    } catch {
      return null;
    }
  });

  const saveProfile = (data: UserProfile) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(data));
    setProfile(data);
  };

  const clearProfile = () => {
    localStorage.removeItem(PROFILE_KEY);
    setProfile(null);
  };

  return { profile, saveProfile, clearProfile };
}
