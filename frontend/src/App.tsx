import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom"

import { AppShell } from "@/components/AppShell"
import { Skeleton } from "@/components/ui/skeleton"
import { AuthProvider, useAuth } from "@/lib/auth"
import { DashboardPage } from "@/pages/DashboardPage"
import { LoginPage } from "@/pages/LoginPage"
import { RegisterPage } from "@/pages/RegisterPage"
import { UsersPage } from "@/pages/UsersPage"

function RequireAuth() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <main className="flex min-h-svh items-center justify-center p-6">
        <Skeleton className="h-10 w-48" />
      </main>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
