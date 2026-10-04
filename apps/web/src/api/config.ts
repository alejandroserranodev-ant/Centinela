import { bearer } from './session';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_HEADERS = {
  'Content-Type': 'application/json',
};

export function authHeaders(): Record<string, string> {
  return { ...API_HEADERS, ...bearer() };
}
