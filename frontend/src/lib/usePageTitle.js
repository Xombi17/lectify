import { useEffect } from "react";

/** Per-page browser tab title, e.g. usePageTitle("Library") -> "Library · Lectify". */
export function usePageTitle(title) {
    useEffect(() => {
        document.title = title ? `${title} · Lectify` : "Lectify";
    }, [title]);
}
