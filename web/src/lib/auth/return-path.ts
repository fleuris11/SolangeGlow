/**
 * Where to go back after signing in (a visitor who wanted to buy is brought back to the
 * product). Kept for the tab only; storage may be refused (private mode): then home.
 */
const KEY = "sg.return-to";

export function rememberReturnPath(path: string) {
  try {
    sessionStorage.setItem(KEY, path);
  } catch {
    // Storage refused: the person lands on the home page, nothing breaks.
  }
}

export function takeReturnPath(): string | null {
  try {
    const path = sessionStorage.getItem(KEY);
    sessionStorage.removeItem(KEY);
    return path && path.startsWith("/") && !path.startsWith("//") ? path : null;
  } catch {
    return null;
  }
}
