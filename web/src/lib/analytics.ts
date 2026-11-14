/** Key moments → Meta standard events (only when the pixel was accepted: lib/consent). */
const META_EVENTS = {
  signup: "CompleteRegistration",
  booking: "Schedule",
  order: "Purchase",
  // Counted when the giver leaves for the payment page: the payment itself is not known here.
  gift: "InitiateCheckout",
} as const;

type Tracked = keyof typeof META_EVENTS;
type Fbq = (command: "track", event: string, data?: Record<string, unknown>) => void;

/**
 * A key moment counted by the audience tool (Umami, no cookies) and, after a « yes » in the
 * cookie banner, by the Meta pixel. Nothing when they are off. `value` in euros, for orders.
 */
export function track(event: Tracked, value?: { amount: number; currency: string }): void {
  try {
    (window as unknown as { umami?: { track: (name: string) => void } }).umami?.track(event);
  } catch {
    // never break a screen for a statistic
  }
  try {
    const fbq = (window as unknown as { fbq?: Fbq }).fbq;
    if (!fbq) return;
    const data = value ? { value: value.amount, currency: value.currency } : undefined;
    fbq("track", META_EVENTS[event], data);
  } catch {
    // same
  }
}
