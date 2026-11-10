import { useCallback, useEffect, useState } from "react"
import { Navigate } from "react-router-dom"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth } from "@/lib/auth"
import { api, type User, type UserListResponse } from "@/lib/api"

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—"
  }
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString()
}

export function UsersPage() {
  const { isAdmin, user: currentUser } = useAuth()
  const [items, setItems] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const res = await api<UserListResponse>("/users")
      setItems(res.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isAdmin) {
      void load()
    }
  }, [isAdmin, load])

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  async function onRoleChange(userId: string, role: string) {
    setBusyId(userId)
    setError(null)
    try {
      const updated = await api<User>(`/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      })
      setItems((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: updated.role } : u)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update role")
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="flex flex-col gap-4 py-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="text-sm text-muted-foreground">
          Manage roles for portal accounts.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Skeleton className="h-8 w-full" />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="h-24 text-center text-muted-foreground"
                >
                  No users found.
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-medium">{row.email}</TableCell>
                  <TableCell>{row.full_name ?? "—"}</TableCell>
                  <TableCell>
                    <select
                      className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50"
                      value={row.role}
                      disabled={
                        busyId === row.id || row.id === currentUser?.id
                      }
                      aria-label={`Role for ${row.email}`}
                      onChange={(ev) =>
                        void onRoleChange(row.id, ev.target.value)
                      }
                    >
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                    </select>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(row.created_at)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
