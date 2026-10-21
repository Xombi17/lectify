import * as React from "react"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border border-border px-3 py-0.5 text-sm font-medium",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground border-primary",
        secondary:
          "bg-muted text-foreground border-border",
        destructive:
          "bg-destructive text-destructive-foreground border-destructive",
        outline: "bg-transparent text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  ...props
}) {
  return (<div className={cn(badgeVariants({ variant }), className)} {...props} />);
}

export { Badge, badgeVariants }
