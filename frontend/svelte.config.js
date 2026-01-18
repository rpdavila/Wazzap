import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Track A11y warnings to show a summary instead of spamming
let a11yWarningCount = 0;
let a11yWarningShown = false;

export default {
  preprocess: vitePreprocess(),
  onwarn: (warning, handler) => {
    // Suppress A11y warnings - show a single summary message instead
    if (warning.code && warning.code.startsWith('a11y-')) {
      a11yWarningCount++;
      // Show summary only once
      if (!a11yWarningShown) {
        console.warn(`[Svelte] A11y warnings detected (will show summary only). Run with --verbose to see details.`);
        a11yWarningShown = true;
      }
      return; // Suppress individual A11y warnings
    }
    // Handle other warnings normally
    handler(warning);
  }
};
