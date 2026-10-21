"use client";

// Last-resort boundary: replaces the whole document when the root layout itself fails.
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
          textAlign: "center",
          padding: 24,
        }}
      >
        <h1 style={{ fontSize: 32, margin: 0 }}>Lectify hit a problem</h1>
        <p style={{ maxWidth: 420, color: "#555", margin: 0 }}>
          Something broke while loading the app. Reloading usually fixes it.
        </p>
        <button
          type="button"
          onClick={reset}
          style={{ padding: "10px 20px", border: 0, background: "#1e3a5f", color: "#fff", cursor: "pointer" }}
        >
          Reload
        </button>
      </body>
    </html>
  );
}
