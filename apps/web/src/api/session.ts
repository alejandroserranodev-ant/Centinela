const STORAGE_KEY = 'centinela.token';

let token: string | null | undefined;
let unauthorized: (() => void) | null = null;

function storage(): Storage | null {
  try {
    return globalThis.sessionStorage ?? null;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  if (token === undefined) {
    try {
      token = storage()?.getItem(STORAGE_KEY) ?? null;
    } catch {
      token = null;
    }
  }
  return token;
}

export function setToken(next: string | null): void {
  token = next;
  try {
    if (next) {
      storage()?.setItem(STORAGE_KEY, next);
    } else {
      storage()?.removeItem(STORAGE_KEY);
    }
  } catch {
    return;
  }
}

export function onUnauthorized(callback: (() => void) | null): void {
  unauthorized = callback;
}

export function notifyUnauthorized(): void {
  setToken(null);
  unauthorized?.();
}

export function bearer(): Record<string, string> {
  const current = getToken();
  return current ? { Authorization: `Bearer ${current}` } : {};
}
