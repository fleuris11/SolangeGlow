/** A product chosen before signing in: added to the cart once the person is back. */
const KEY = "sg.pending-cart";

export type PendingItem = { variant_id?: string; bundle_id?: string; quantity: number };

export function rememberPending(item: PendingItem) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(item));
  } catch {
    // Storage refused: she adds it again after signing in.
  }
}

export function takePending(): PendingItem | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    sessionStorage.removeItem(KEY);
    return raw ? (JSON.parse(raw) as PendingItem) : null;
  } catch {
    return null;
  }
}
