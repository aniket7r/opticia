import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center animate-fade-in">
      <div className="text-center">
        <h1 className="mb-2 text-6xl font-bold text-foreground">404</h1>
        <p className="mb-6 text-muted-foreground">This page doesn&apos;t exist.</p>
        <Link
          href="/"
          className="tap-target inline-flex items-center rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-default hover:bg-primary/90"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
