// Re-export HTTP client as the main API client
export { ApiError } from './http-client';
export {
  advanceDay,
  chat,
  decide,
  getAlert,
  getInboxSummary,
  getQuery,
  getSettings,
  getSimulationState,
  listAlerts,
  listBitacora,
  saveSettings,
} from './http-client';
