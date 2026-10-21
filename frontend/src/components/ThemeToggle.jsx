import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { MoonStars, Sun } from "@/components/icons";
import { Button } from "@/components/ui/button";

export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Same-size placeholder before mount avoids a hydration mismatch.
  if (!mounted) return <Button variant="ghost" size="icon" aria-label="Switch colour theme" data-testid="theme-toggle" className="rounded-full" disabled />;

  const dark = resolvedTheme === "dark";
  const label = dark ? "Switch to light theme" : "Switch to dark theme";
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={label}
      title={label}
      data-testid="theme-toggle"
      className="rounded-full"
      onClick={() => setTheme(dark ? "light" : "dark")}
    >
      {dark ? <Sun size={18} aria-hidden="true" /> : <MoonStars size={18} aria-hidden="true" />}
    </Button>
  );
}
