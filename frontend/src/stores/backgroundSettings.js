import { writable } from 'svelte/store';

// Unannoying color palette - Back Color (primary) and Front Color (secondary)
const NICE_COLORS = [
  { primary: '#e5e5f7', secondary: '#444cf7' }, // Light purple background, blue pattern
  { primary: '#f0f0f5', secondary: '#6366f1' }, // Light gray background, indigo pattern
  { primary: '#f5f5fa', secondary: '#8b5cf6' }, // Light purple background, purple pattern
  { primary: '#fafbfc', secondary: '#3b82f6' }, // Light gray background, blue pattern
  { primary: '#f8f9fa', secondary: '#10b981' }, // Light gray background, green pattern
  { primary: '#f1f5f9', secondary: '#0ea5e9' }  // Light blue-gray background, sky blue pattern
];

const PATTERN_TYPES = ['zigzag', 'isometric', 'polka', 'polka-v2', 'cross'];

function getRandomSettings() {
  const randomColor = NICE_COLORS[Math.floor(Math.random() * NICE_COLORS.length)];
  const randomPattern = PATTERN_TYPES[Math.floor(Math.random() * PATTERN_TYPES.length)];
  
  return {
    primaryColor: randomColor.primary,
    secondaryColor: randomColor.secondary,
    opacity: 0.8, // Match magicpattern.design default
    spacing: 30,
    patternType: randomPattern
  };
}

const DEFAULT_SETTINGS = getRandomSettings();

function createBackgroundSettingsStore() {
  // Load from localStorage, or use random if not set
  let initialSettings = DEFAULT_SETTINGS;
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('backgroundSettings');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Fix black colors - replace with defaults
        if (parsed.primaryColor === '#000000' || parsed.primaryColor === '#000' || !parsed.primaryColor) {
          parsed.primaryColor = '#e5e5f7';
        }
        if (parsed.secondaryColor === '#000000' || parsed.secondaryColor === '#000' || !parsed.secondaryColor) {
          parsed.secondaryColor = '#444cf7';
        }
        // Ensure all required fields exist
        initialSettings = { ...DEFAULT_SETTINGS, ...parsed };
      } catch (e) {
        console.error('Failed to parse background settings:', e);
        initialSettings = getRandomSettings();
      }
    } else {
      // First time - use random settings
      initialSettings = getRandomSettings();
      localStorage.setItem('backgroundSettings', JSON.stringify(initialSettings));
    }
  }

  const { subscribe, set, update } = writable(initialSettings);

  return {
    subscribe,
    update: (newSettings) => {
      const updated = { ...initialSettings, ...newSettings };
      set(updated);
      if (typeof window !== 'undefined') {
        localStorage.setItem('backgroundSettings', JSON.stringify(updated));
      }
    },
    reset: () => {
      const randomSettings = getRandomSettings();
      set(randomSettings);
      if (typeof window !== 'undefined') {
        localStorage.setItem('backgroundSettings', JSON.stringify(randomSettings));
      }
    }
  };
}

export const backgroundSettings = createBackgroundSettingsStore();
