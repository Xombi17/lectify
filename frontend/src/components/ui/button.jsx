import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

// Editorial buttons: filled accent (pen) / hairline outline (default) / ghost (quiet).
const OUTLINE = "bg-card text-foreground border-border hover:bg-muted hover:border-input active:bg-accent"
const QUIET = "bg-transparent border-transparent text-muted-foreground hover:bg-muted hover:text-foreground active:bg-accent"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--r)] min-h-11 text-base font-medium border transition-[background-color,border-color,color,transform] duration-150 ease-out active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45 motion-reduce:transition-none motion-reduce:active:scale-100 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: OUTLINE,
        pen: "bg-primary text-primary-foreground border-primary hover:bg-primary/90",
        quiet: QUIET,
        destructive:
          "bg-destructive text-destructive-foreground border-destructive hover:bg-destructive/90",
        link: "border-transparent min-h-0 text-primary underline decoration-1 underline-offset-4 hover:decoration-2 active:scale-100",
        // aliases so legacy call sites keep working
        ghost: QUIET,
        outline: OUTLINE,
        secondary: OUTLINE,
      },
      size: {
        default: "px-5",
        sm: "px-3 text-sm",
        lg: "px-6",
        icon: "h-11 w-11 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props} />
  );
})
Button.displayName = "Button"

export { Button, buttonVariants }
