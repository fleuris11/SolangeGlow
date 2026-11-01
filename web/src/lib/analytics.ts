/** A key moment counted by the audience tool (Umami, no cookies); nothing when it is off. */
export function track(event: "signup" | "booking" | "order" | "gift"): void {
  try {
    (window as unknown as { umami?: { track: (name: string) => void } }).umami?.track(event);
  } catch {
    // never break a screen for a statistic
  }
}
