// Frontend-only onboarding state — no backend flag exists for "has completed
// onboarding", so this is tracked per-user in localStorage on this device.
// A brand-new account is "pending" until the user dismisses the checklist or
// finishes every step; existing accounts are never touched.
const KEY_PREFIX = "subly.onboarding.";

type OnboardingState = "pending" | "dismissed";

function key(userId: string): string {
  return `${KEY_PREFIX}${userId}`;
}

function read(userId: string): OnboardingState | null {
  try {
    const raw = localStorage.getItem(key(userId));
    return raw === "pending" || raw === "dismissed" ? raw : null;
  } catch {
    return null;
  }
}

// Call once, right after a successful /auth/register — never after login.
export function markOnboardingStarted(userId: string): void {
  try {
    localStorage.setItem(key(userId), "pending");
  } catch {
    /* private mode / storage disabled — onboarding just won't persist */
  }
}

export function dismissOnboarding(userId: string): void {
  try {
    localStorage.setItem(key(userId), "dismissed");
  } catch {
    /* ignore */
  }
}

export function isOnboardingDismissed(userId: string): boolean {
  return read(userId) === "dismissed";
}
