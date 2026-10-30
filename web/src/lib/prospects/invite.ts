/**
 * The code of an invitation link (/pro/start?invite=CODE), kept in this browser until the
 * new pro opens her showcase: the team then sees in its prospecting file that she signed up.
 */
const KEY = "sg_invite";

export function rememberInvite(code: string): void {
  try {
    if (/^[\w-]{4,40}$/.test(code)) localStorage.setItem(KEY, code);
  } catch {
    // Storage blocked: the invitation is simply not followed.
  }
}

export function takeInvite(): string | null {
  try {
    const code = localStorage.getItem(KEY);
    localStorage.removeItem(KEY);
    return code;
  } catch {
    return null;
  }
}
