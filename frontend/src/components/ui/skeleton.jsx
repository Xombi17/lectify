import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}) {
  return (
    <div
      aria-hidden="true"
      className={cn("sk", className)}
      {...props} />
  );
}

export { Skeleton }
