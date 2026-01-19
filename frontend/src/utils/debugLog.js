/**
 * Debug logging utility
 * Only logs if VITE_DEBUG_LOG_URL is set in environment variables
 * For production, leave this unset to disable all debug logging
 */

const DEBUG_LOG_URL = import.meta.env.VITE_DEBUG_LOG_URL;

/**
 * Log debug information to an external service
 * @param {string} location - Code location (e.g., 'file.js:123')
 * @param {string} message - Log message
 * @param {object} data - Additional data to log
 * @param {string} hypothesisId - Optional hypothesis ID
 */
export function debugLog(location, message, data = null, hypothesisId = null) {
  // Only log if DEBUG_LOG_URL is configured
  if (!DEBUG_LOG_URL) {
    return;
  }

  try {
    const logData = {
      location,
      message,
      data: data || {},
      timestamp: Date.now(),
      sessionId: 'debug-session',
      runId: 'run1',
      hypothesisId: hypothesisId || null
    };

    // Use fetch with catch to silently fail if logging service is unavailable
    fetch(DEBUG_LOG_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(logData)
    }).catch(() => {
      // Silently fail - debug logging should never break the app
    });
  } catch (error) {
    // Silently fail - debug logging should never break the app
  }
}
