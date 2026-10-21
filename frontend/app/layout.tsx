import type { Metadata, Viewport } from "next";
import { Inter, Newsreader, Geist_Mono } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

// Two families + mono: Newsreader (display/reading serif) and Inter (UI sans). Weights 400/500 only.
const sans = Inter({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-sans", display: "swap" });
const serif = Newsreader({ subsets: ["latin"], weight: ["400", "500"], style: ["normal", "italic"], variable: "--font-serif", display: "swap" });
const mono = Geist_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Lectify",
  description: "Lecture notes, quizzes and flashcards, written up from every class.",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  manifest: "/site.webmanifest",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf9f5" },
    { media: "(prefers-color-scheme: dark)", color: "#181715" },
  ],
};

// Static pre-paint theme script: only "light"/"dark" are applied (next-themes may store "system").
const THEME_SCRIPT = `try{var t=localStorage.getItem("lectify-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${sans.variable} ${serif.variable} ${mono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:inline-flex focus:min-h-11 focus:items-center focus:rounded-lg focus:border focus:border-border focus:bg-card focus:px-4 focus:shadow-float focus:text-foreground"
        >
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
