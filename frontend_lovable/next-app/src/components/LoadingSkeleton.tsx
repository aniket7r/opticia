import { Skeleton } from "@/components/ui/skeleton";

export function PageSkeleton() {
  return (
    <div className="container py-10 animate-fade-in">
      <Skeleton className="mb-4 h-8 w-48" />
      <Skeleton className="mb-2 h-4 w-72" />
      <Skeleton className="mb-8 h-4 w-56" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32 rounded-lg" />
        ))}
      </div>
    </div>
  );
}
