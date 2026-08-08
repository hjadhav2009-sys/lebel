export class APIClientError extends Error { constructor(public code:string, message:string, public details:Record<string,unknown>={}) { super(message); } }

export async function api<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ code:"request_failed", message:`Request failed (${response.status})`, details:{} }));
    const error = body.detail ?? body;
    throw new APIClientError(error.code ?? "request_failed", error.message ?? "Request failed", error.details ?? {});
  }
  return response.json();
}

export function queryString(values:Record<string,string|number|boolean|undefined|null>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key,value]) => { if (value !== undefined && value !== null && value !== "") params.set(key,String(value)); });
  return params.toString();
}
