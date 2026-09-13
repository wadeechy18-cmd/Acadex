import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

const SCHOOL_FEATURES = [
  "Manage teachers",
  "Manage classes",
  "Create timetables",
  "Handle teacher absences",
  "Automatically arrange cover",
  "View teacher lesson plans",
];

const TEACHER_FEATURES = [
  "English National Curriculum",
  "AI-assisted lesson planning",
  "Lesson resources",
  "Step-by-step lesson structure",
  "Homework",
  "Lesson overview",
];

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="container flex items-center justify-between py-5">
          <span className="text-xl font-bold text-primary">Acadex</span>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/login" className="text-muted-foreground hover:text-foreground">
              Log in
            </Link>
          </nav>
        </div>
      </header>

      <section className="container flex flex-col items-center py-20 text-center">
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          Smarter Teaching. Better Planning. Less Admin.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
          Acadex helps teachers create high-quality lesson plans aligned with the English
          National Curriculum, while helping schools manage teachers, classes, lesson planning
          and timetable changes.
        </p>
        <p className="mt-10 text-sm font-medium text-muted-foreground">How would you like to use Acadex?</p>
      </section>

      <section className="container grid gap-6 pb-24 sm:grid-cols-3">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>School</CardTitle>
            <CardDescription>Manage your school</CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
              {SCHOOL_FEATURES.map((f) => (
                <li key={f}>• {f}</li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Link href="/register/school" className="w-full">
              <Button className="w-full">Continue as School</Button>
            </Link>
          </CardFooter>
        </Card>

        <Card className="flex flex-col border-primary/30 shadow-md">
          <CardHeader>
            <CardTitle>Teacher</CardTitle>
            <CardDescription>Plan lessons faster</CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
              {TEACHER_FEATURES.map((f) => (
                <li key={f}>• {f}</li>
              ))}
            </ul>
          </CardContent>
          <CardFooter>
            <Link href="/register/teacher" className="w-full">
              <Button className="w-full">Continue as Teacher</Button>
            </Link>
          </CardFooter>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Student</CardTitle>
            <CardDescription>Learning platform</CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            <p className="text-sm text-muted-foreground">Student learning is coming soon.</p>
          </CardContent>
          <CardFooter>
            <Link href="/student" className="w-full">
              <Button className="w-full" variant="secondary">
                Coming Soon
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </section>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} Acadex.
      </footer>
    </main>
  );
}
