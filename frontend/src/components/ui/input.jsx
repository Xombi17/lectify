import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex min-h-11 w-full bg-card text-base text-foreground border border-input rounded-[var(--r)] hover:border-foreground/60 focus-visible:border-primary px-3 py-2 transition-colors placeholder:text-muted-foreground aria-[invalid=true]:border-destructive disabled:cursor-not-allowed disabled:opacity-45 file:border-0 file:bg-transparent file:text-sm file:font-bold file:text-foreground",
        className
      )}
      ref={ref}
      {...props} />
  );
})
Input.displayName = "Input"

export { Input }
