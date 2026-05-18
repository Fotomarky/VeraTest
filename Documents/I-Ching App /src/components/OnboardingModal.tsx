import React, { useEffect, useRef, useState } from 'react';
import type { UserProfile } from '../hooks/useProfile';
import { t } from '../i18n';

const s = t();

const STEPS: Step[] = ['name', 'age', 'welcome'];

interface Props {
  isOpen: boolean;
  onComplete: (profile: UserProfile) => void;
}

type Step = 'name' | 'age' | 'welcome';

const OnboardingModal: React.FC<Props> = ({ isOpen, onComplete }) => {
  const [step, setStep] = useState<Step>('name');
  const [name, setName] = useState('');
  const [ageRaw, setAgeRaw] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const submittedRef = useRef(false);

  useEffect(() => () => { clearTimeout(timerRef.current); }, []);

  if (!isOpen) return null;

  const handleNameNext = () => {
    if (!name.trim()) return;
    setStep('age');
  };

  const handleAgeNext = () => {
    if (submittedRef.current) return;
    const age = parseInt(ageRaw, 10);
    if (!age || age < 1 || age > 120) return;
    submittedRef.current = true;
    setStep('welcome');
    timerRef.current = setTimeout(() => onComplete({ name: name.trim(), age }), 1600);
  };

  const currentIndex = STEPS.indexOf(step);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in px-6">
      <div className="w-full max-w-[380px] bg-[#0f1a14] border border-[#d4af37]/30 rounded-2xl px-8 py-10 shadow-2xl flex flex-col items-center gap-6">

        {/* Step indicator */}
        <div className="flex gap-2" aria-hidden="true">
          {STEPS.map((stepKey, i) => (
            <div
              key={stepKey}
              className={`h-1.5 rounded-full transition-all duration-500 ${
                step === stepKey ? 'w-8 bg-[#d4af37]' : i < currentIndex ? 'w-4 bg-[#d4af37]/50' : 'w-4 bg-white/15'
              }`}
            />
          ))}
        </div>

        {step === 'name' && (
          <>
            <p className="font-display text-[1.25rem] text-[#e3d1a8] text-center leading-snug">
              {s.onboardingNamePrompt}
            </p>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNameNext()}
              placeholder="…"
              maxLength={40}
              className="w-full bg-[#eeeadd]/90 border-2 border-[#b89552] rounded-full py-3 px-5 text-[#2c221a] placeholder-[#7a6040] font-body text-lg text-center focus:outline-none focus:ring-2 focus:ring-[#d4af37]/50"
            />
            <button
              onClick={handleNameNext}
              disabled={!name.trim()}
              className="w-full bg-[#d4af37] text-[#1a1208] font-display rounded-full py-3 text-lg tracking-wide disabled:opacity-40 hover:bg-[#c9a653] transition-colors"
            >
              {s.onboardingNext}
            </button>
          </>
        )}

        {step === 'age' && (
          <>
            <p className="font-display text-[1.25rem] text-[#e3d1a8] text-center leading-snug">
              {s.onboardingAgePrompt}
            </p>
            <input
              autoFocus
              type="number"
              inputMode="numeric"
              value={ageRaw}
              onChange={(e) => setAgeRaw(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAgeNext()}
              placeholder={s.onboardingAgePlaceholder}
              min={1}
              max={120}
              className="w-full bg-[#eeeadd]/90 border-2 border-[#b89552] rounded-full py-3 px-5 text-[#2c221a] placeholder-[#7a6040] font-body text-lg text-center focus:outline-none focus:ring-2 focus:ring-[#d4af37]/50"
            />
            <button
              onClick={handleAgeNext}
              disabled={!ageRaw || parseInt(ageRaw, 10) < 1 || parseInt(ageRaw, 10) > 120}
              className="w-full bg-[#d4af37] text-[#1a1208] font-display rounded-full py-3 text-lg tracking-wide disabled:opacity-40 hover:bg-[#c9a653] transition-colors"
            >
              {s.onboardingNext}
            </button>
          </>
        )}

        {step === 'welcome' && (
          <div className="flex flex-col items-center gap-4 animate-fade-in" aria-live="polite">
            <div className="text-4xl">☯</div>
            <p className="font-display text-[1.5rem] text-[#d4af37] text-center">
              {s.welcomeBack(name.trim())}
            </p>
            <p className="font-display italic text-[#e3d1a8]/70 text-center text-sm">
              {s.appSubtitle}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingModal;
