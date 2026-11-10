/** Fill last 30 calendar days with zero counts for missing dates. */
export function padSignupsByDay(
  rows: { date: string; count: number }[],
): { date: string; count: number }[] {
  const byDate = new Map(rows.map((r) => [r.date, r.count]))
  const out: { date: string; count: number }[] = []
  const end = new Date()
  end.setUTCHours(0, 0, 0, 0)
  for (let i = 29; i >= 0; i--) {
    const d = new Date(end)
    d.setUTCDate(d.getUTCDate() - i)
    const iso = d.toISOString().slice(0, 10)
    out.push({ date: iso, count: byDate.get(iso) ?? 0 })
  }
  return out
}
