import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

function App() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center bg-background p-6 text-foreground">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Portal</CardTitle>
          <CardDescription>
            Vite + shadcn with Catppuccin theme
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-end">
          <Button type="button">Continue</Button>
        </CardContent>
      </Card>
    </main>
  )
}

export default App
