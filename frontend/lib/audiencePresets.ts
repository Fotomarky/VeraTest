// Preset option library for the chip selector on /new.
// Edit this file to add/remove options — no backend changes required.
//
// Chip groups feed straight into the AudiencePreset schema in
// simab/models.py. Keep keys aligned: age_ranges, roles, industries,
// interests, behaviors, devices.

export type PresetKey =
  | "age_ranges"
  | "roles"
  | "industries"
  | "interests"
  | "behaviors"
  | "devices";

export interface PresetGroup {
  key: PresetKey;
  label: string;
  options: string[];
  inlineCount?: number; // how many to show before "+ more" expand (default 8)
}

export const PRESET_GROUPS: PresetGroup[] = [
  {
    key: "age_ranges",
    label: "Age range",
    options: ["18–24", "25–34", "35–44", "45–54", "55–64", "65+"],
    inlineCount: 6,
  },
  {
    key: "roles",
    label: "Role / life stage",
    options: [
      "Student",
      "Founder",
      "IC engineer",
      "Engineering manager",
      "Designer",
      "Marketer",
      "Product manager",
      "Director",
      "C-level",
      "Sales rep",
      "Consultant",
      "Freelancer",
      "Operations lead",
      "Customer support",
      "Parent",
      "Retiree",
    ],
  },
  {
    key: "industries",
    label: "Industry",
    options: [
      "SaaS",
      "E-commerce",
      "FinTech",
      "Healthcare",
      "Education",
      "Media",
      "Travel",
      "Real estate",
      "Manufacturing",
      "Logistics",
      "Agency",
      "Non-profit",
    ],
  },
  {
    key: "interests",
    label: "Topical interest",
    options: [
      "Tech",
      "Design",
      "Marketing",
      "Finance",
      "Health & fitness",
      "Sustainability",
      "Productivity",
      "Travel",
      "Fashion",
      "Food",
      "Gaming",
      "Parenting",
    ],
  },
  {
    key: "behaviors",
    label: "Decision behavior",
    options: [
      "Comparison shopper",
      "Impulse buyer",
      "Brand loyal",
      "Deal hunter",
      "Early adopter",
      "Skeptic",
      "Research-heavy",
      "Recommendation-driven",
      "Risk-averse",
      "Price-insensitive",
    ],
  },
  {
    key: "devices",
    label: "Device",
    options: ["Desktop", "Mobile", "Tablet"],
    inlineCount: 3,
  },
];

export type AudiencePreset = Record<PresetKey, string[]> & { notes?: string };

export function emptyPreset(): AudiencePreset {
  return {
    age_ranges: [],
    roles: [],
    industries: [],
    interests: [],
    behaviors: [],
    devices: [],
    notes: "",
  };
}

export function isEmptyPreset(p: AudiencePreset): boolean {
  return (
    p.age_ranges.length === 0 &&
    p.roles.length === 0 &&
    p.industries.length === 0 &&
    p.interests.length === 0 &&
    p.behaviors.length === 0 &&
    p.devices.length === 0 &&
    !(p.notes && p.notes.trim())
  );
}

// "Random sensible default" — picks a small, coherent set rather than truly
// random combos (avoids absurd intersections like Retiree + IC engineer).
// Useful as a one-click demo or as a sanity placeholder for first-time users.
const SENSIBLE_DEFAULTS: AudiencePreset[] = [
  {
    age_ranges: ["25–34", "35–44"],
    roles: ["Founder", "Product manager"],
    industries: ["SaaS"],
    interests: ["Tech", "Productivity"],
    behaviors: ["Comparison shopper", "Research-heavy"],
    devices: ["Desktop"],
    notes: "",
  },
  {
    age_ranges: ["25–34"],
    roles: ["Marketer", "Designer"],
    industries: ["E-commerce"],
    interests: ["Fashion", "Marketing"],
    behaviors: ["Impulse buyer", "Recommendation-driven"],
    devices: ["Mobile"],
    notes: "",
  },
  {
    age_ranges: ["35–44", "45–54"],
    roles: ["Director", "Operations lead"],
    industries: ["Logistics", "Manufacturing"],
    interests: ["Finance"],
    behaviors: ["Research-heavy", "Risk-averse"],
    devices: ["Desktop"],
    notes: "",
  },
];

export function randomSensibleDefault(): AudiencePreset {
  return SENSIBLE_DEFAULTS[Math.floor(Math.random() * SENSIBLE_DEFAULTS.length)];
}

// localStorage helpers
const LS_KEY = "simab.lastAudience";

export function saveLastPreset(p: AudiencePreset): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(p));
  } catch {
    // ignore quota / private-mode errors
  }
}

export function loadLastPreset(): AudiencePreset | null {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return {
      age_ranges: parsed.age_ranges || [],
      roles: parsed.roles || [],
      industries: parsed.industries || [],
      interests: parsed.interests || [],
      behaviors: parsed.behaviors || [],
      devices: parsed.devices || [],
      notes: parsed.notes || "",
    };
  } catch {
    return null;
  }
}
