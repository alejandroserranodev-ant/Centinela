export function messageOfError(body: string, statusText: string): string {
  try {
    const detail = (JSON.parse(body) as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: unknown } | undefined;
      if (typeof first?.msg === 'string' && first.msg) {
        return first.msg;
      }
    }
  } catch {
    return body || statusText;
  }
  return body || statusText;
}
