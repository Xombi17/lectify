import { useState } from "react";
import { Eye, EyeSlash } from "@/components/icons";
import { Input } from "@/components/ui/input";

/** Password field with a show/hide toggle. Pass autoComplete="new-password" for new/changed passwords. */
export default function PasswordInput({ id, className = "", ...props }) {
    const [show, setShow] = useState(false);
    return (
        <div className="relative">
            <Input id={id} type={show ? "text" : "password"} className={`pr-11 ${className}`} {...props} />
            <button
                type="button"
                onClick={() => setShow((v) => !v)}
                aria-label={show ? "Hide password" : "Show password"}
                aria-pressed={show}
                className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-muted-foreground hover:text-foreground"
            >
                {show ? <EyeSlash size={18} /> : <Eye size={18} />}
            </button>
        </div>
    );
}
