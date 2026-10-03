// API configuration
// Use environment variables or defaults for local development

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const DEFAULT_USER = {
  name: 'Usuario Demo',
  role: 'gerente' as const,
};

export const API_HEADERS = {
  'Content-Type': 'application/json',
};

export function getDecisionHeaders() {
  return {
    ...API_HEADERS,
    'X-User-Name': encodeURIComponent(DEFAULT_USER.name),
    'X-User-Role': DEFAULT_USER.role,
  };
}
