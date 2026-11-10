import { useEffect, useState } from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type DashboardStats } from "@/lib/api"
import { padSignupsByDay } from "@/lib/chart-data"

const chartConfig = {
  signups: {
    label: "Signups",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await api<DashboardStats>("/dashboard/stats")
        if (!cancelled) {
          setStats(data)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load stats")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const chartData = stats
    ? padSignupsByDay(stats.signups_by_day).map((row) => ({
        date: row.date,
        signups: row.count,
      }))
    : []

  return (
    <div className="flex flex-col gap-4 py-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          User aggregates from the live database.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))
          : stats
            ? (
                [
                  { label: "Total users", value: stats.total_users },
                  { label: "New users (30d)", value: stats.new_users_30d },
                  { label: "Admins", value: stats.admin_count },
                  { label: "Standard users", value: stats.user_count },
                ] as const
              ).map((metric) => (
                <Card key={metric.label}>
                  <CardHeader className="pb-2">
                    <CardDescription>{metric.label}</CardDescription>
                    <CardTitle className="text-3xl tabular-nums">
                      {metric.value.toLocaleString()}
                    </CardTitle>
                  </CardHeader>
                </Card>
              ))
            : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Signups by day</CardTitle>
          <CardDescription>Last 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-[280px] w-full" />
          ) : (
            <ChartContainer config={chartConfig} className="h-[280px] w-full">
              <AreaChart
                data={chartData}
                margin={{ left: 0, right: 8, top: 8, bottom: 0 }}
              >
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  minTickGap={24}
                  tickFormatter={(value: string) =>
                    new Date(value + "T00:00:00Z").toLocaleDateString(
                      undefined,
                      { month: "short", day: "numeric" },
                    )
                  }
                />
                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  width={32}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      labelFormatter={(value) =>
                        new Date(String(value) + "T00:00:00Z").toLocaleDateString()
                      }
                    />
                  }
                />
                <Area
                  type="monotone"
                  dataKey="signups"
                  fill="var(--color-signups)"
                  fillOpacity={0.35}
                  stroke="var(--color-signups)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
