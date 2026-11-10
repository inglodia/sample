const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api"

function resolveUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path
  }
  if (path.startsWith("/api")) {
    return path
  }
  const segment = path.startsWith("/") ? path : `/${path}`
  return `${API_BASE.replace(/\/$/, "")}${segment}`
}

async function readErrorMessage(res: Response): Promise<string> {
  const text = await res.text()
  try {
    const body = JSON.parse(text) as { detail?: string | unknown[] }
    if (typeof body.detail === "string") {
      return body.detail
    }
    if (Array.isArray(body.detail)) {
      return body.detail.map((d) => String(d)).join(", ")
    }
  } catch {
    /* not JSON */
  }
  return text || res.statusText || "Request failed"
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(resolveUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const message = await readErrorMessage(res)
    throw Object.assign(new Error(message), { status: res.status })
  }
  if (res.status === 204) {
    return undefined as T
  }
  const contentType = res.headers.get("content-type") ?? ""
  if (!contentType.includes("application/json")) {
    return undefined as T
  }
  // Allow explicit JSON null (e.g. GET /auth/me when logged out).
  return (await res.json()) as T
}

export type User = {
  id: string
  email: string
  full_name: string | null
  role: string
  created_at?: string | null
}

export type DashboardStats = {
  total_users: number
  new_users_30d: number
  admin_count: number
  user_count: number
  signups_by_day: { date: string; count: number }[]
}

export type UserListResponse = {
  items: User[]
}
