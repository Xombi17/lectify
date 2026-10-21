"use client";

import { useRef, useState } from "react";
import { Play, Pause } from "@/components/icons";

const fmt = (s) => {
    const t = Math.max(0, Math.floor(Number.isFinite(s) ? s : 0));
    return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
};

// startAt: resume position in seconds. onProgress(seconds): called about every 5 s, on pause, and with 0 at the end.
export default function PenPlayer({ src, startAt = 0, onProgress }) {
    const ref = useRef(null);
    const lastReported = useRef(0);
    const [playing, setPlaying] = useState(false);
    const [current, setCurrent] = useState(0);
    const [duration, setDuration] = useState(0);

    const seek = (t) => {
        const a = ref.current;
        if (!a) return;
        const next = Math.min(Math.max(0, t), duration || 0);
        a.currentTime = next;
        setCurrent(next);
    };
    const toggle = () => {
        const a = ref.current;
        if (!a) return;
        if (playing) a.pause();
        else a.play?.();
    };
    const onKey = (e) => {
        const step = { ArrowRight: 5, ArrowLeft: -5 }[e.key];
        if (step !== undefined) seek((ref.current?.currentTime ?? current) + step);
        else if (e.key === "Home") seek(0);
        else if (e.key === "End") seek(duration);
        else return;
        e.preventDefault();
    };
    const onClick = (e) => {
        const r = e.currentTarget.getBoundingClientRect();
        if (r.width > 0) seek(((e.clientX - r.left) / r.width) * duration);
    };
    const pct = duration > 0 ? Math.min(100, (current / duration) * 100) : 0;

    return (
        <div className="pen-player">
            <audio
                ref={ref}
                data-testid="lecture-audio"
                src={src}
                preload="metadata"
                onPlay={() => setPlaying(true)}
                onPause={(e) => {
                    setPlaying(false);
                    if (!e.currentTarget.ended) onProgress?.(e.currentTarget.currentTime);
                }}
                onEnded={() => {
                    setPlaying(false);
                    onProgress?.(0); // finished: next visit starts from the top
                }}
                onTimeUpdate={(e) => {
                    const t = e.currentTarget.currentTime;
                    setCurrent(t);
                    if (onProgress && Math.abs(t - lastReported.current) >= 5) {
                        lastReported.current = t;
                        onProgress(t);
                    }
                }}
                onLoadedMetadata={(e) => {
                    const d = e.currentTarget.duration || 0;
                    setDuration(d);
                    // resume only when it is meaningful (not the first seconds, not the final seconds)
                    if (startAt > 5 && d > 0 && startAt < d - 5) {
                        e.currentTarget.currentTime = startAt;
                        setCurrent(startAt);
                        lastReported.current = startAt;
                    }
                }}
            />
            <button
                type="button"
                className="play"
                data-testid="pen-play-btn"
                aria-label={playing ? "Pause" : "Play"}
                onClick={toggle}
            >
                {playing ? <Pause size={24} weight="fill" /> : <Play size={24} weight="fill" />}
            </button>
            <div
                className="ink-line cursor-pointer"
                role="slider"
                aria-label="Seek"
                aria-valuemin={0}
                aria-valuemax={Math.round(duration)}
                aria-valuenow={Math.round(current)}
                aria-valuetext={`${fmt(current)} of ${fmt(duration)}`}
                tabIndex={0}
                onKeyDown={onKey}
                onClick={onClick}
            >
                <span style={{ width: `${pct}%` }} />
                <i style={{ left: `${pct}%` }} />
            </div>
            <span className="mono font-mono text-sm">
                {fmt(current)} / {fmt(duration)}
            </span>
        </div>
    );
}
