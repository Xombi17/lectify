import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import ConfirmDialog from "@/components/ConfirmDialog";
import { API, qrApi } from "@/lib/api";
import { QrCode, ArrowClockwise, Download } from "@/components/icons";
import { toast } from "sonner";

function authHeaders() {
    const token = typeof window !== "undefined" ? localStorage.getItem("lm_token") : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function QRCodeCard({ classId, className }) {
    const [qr, setQr] = useState(null);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(false);
    const [regenerating, setRegenerating] = useState(false);
    const [imgUrl, setImgUrl] = useState(null);
    const [downloading, setDownloading] = useState(false);
    const [confirmOpen, setConfirmOpen] = useState(false);

    const load = useCallback(async () => {
        if (!classId) return;
        setLoading(true);
        try {
            const [qrData, analyticsData] = await Promise.all([
                qrApi.get(classId).catch(() => null),
                qrApi.analytics(classId).catch(() => null),
            ]);
            setQr(qrData);
            setAnalytics(analyticsData);
        } finally {
            setLoading(false);
        }
    }, [classId]);

    useEffect(() => {
        if (classId) load();
    }, [classId, load]);

    // The download endpoint requires auth, which a plain <img> can't send —
    // fetch the SVG with the token and render it from a blob URL.
    useEffect(() => {
        if (!classId || !qr) return;
        let cancelled = false;
        let blobUrl = null;
        fetch(`${API}/qr/classes/${classId}/download?format=svg&v=${encodeURIComponent(qr.id || "")}&t=${Date.now()}`, {
            headers: authHeaders(),
            cache: "no-store",
        })
            .then((r) => {
                if (!r.ok) throw new Error(`QR image failed: ${r.status}`);
                return r.blob();
            })
            .then((blob) => {
                if (cancelled) return;
                blobUrl = URL.createObjectURL(blob);
                setImgUrl(blobUrl);
            })
            .catch(() => {
                if (!cancelled) setImgUrl(null);
            });
        return () => {
            cancelled = true;
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
    }, [classId, qr]);

    const handleGenerate = async () => {
        try {
            const newQr = await qrApi.generate(classId);
            setQr(newQr);
            toast.success("QR code generated");
            await load();
        } catch {
            toast.error("Failed to generate QR");
        }
    };

    const handleRegenerate = async () => {
        setRegenerating(true);
        try {
            const newQr = await qrApi.regenerate(classId);
            setQr(newQr);
            toast.success("QR regenerated — old QR invalidated");
            await load();
        } catch {
            toast.error("Failed to regenerate QR");
        } finally {
            setRegenerating(false);
        }
    };

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const r = await fetch(
                `${API}/qr/classes/${classId}/download?format=svg&v=${encodeURIComponent(qr?.id || "")}&t=${Date.now()}`,
                {
                    headers: authHeaders(),
                    cache: "no-store",
                }
            );
            if (!r.ok) throw new Error(`Download failed: ${r.status}`);
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `qr-${classId}.svg`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch {
            toast.error("Failed to download QR");
        } finally {
            setDownloading(false);
        }
    };

    if (loading) {
        return <div className="h-40 animate-pulse rounded-[var(--radius)] border border-border bg-muted/40" />;
    }

    return (
        <Card className="p-6" data-testid={`qr-card-${classId}`}>
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-base">
                    <span className="flex items-center gap-2">
                        <QrCode size={16} weight="regular" className="text-primary" />
                        QR Code
                    </span>
                    {qr?.is_active && (
                        <Badge variant="outline" className="border-primary text-primary">
                            Active
                        </Badge>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent>
                {!qr ? (
                    <div className="py-4 text-center">
                        <p className="mb-3 text-sm text-muted-foreground">No QR code generated</p>
                        <Button variant="pen" onClick={handleGenerate} size="sm" data-testid="generate-qr-btn">
                            Generate QR Code
                        </Button>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-4">
                        {/* QR Image */}
                        <div className="rounded-[var(--r)] border border-border bg-white p-3">
                            {imgUrl ? (
                                <img
                                    src={imgUrl}
                                    alt={`QR code for ${className}`}
                                    className="h-40 w-40"
                                    data-testid="qr-image"
                                />
                            ) : (
                                <div className="flex h-40 w-40 items-center justify-center text-sm text-muted-foreground">
                                    Couldn't load QR image
                                </div>
                            )}
                        </div>

                        {/* Analytics row */}
                        {analytics && (
                            <div className="flex gap-6 text-center">
                                <div>
                                    <div className="font-mono text-2xl font-bold">
                                        {analytics.scan_count}
                                    </div>
                                    <div className="text-overline text-muted-foreground">Scans</div>
                                </div>
                                <div>
                                    <div className="font-mono text-2xl font-bold">
                                        {analytics.enrollment_count}
                                    </div>
                                    <div className="text-overline text-muted-foreground">Enrolled</div>
                                </div>
                                <div>
                                    <div className="font-mono text-2xl font-bold">
                                        {analytics.scan_count > 0
                                            ? `${Math.round((analytics.enrollment_count / analytics.scan_count) * 100)}%`
                                            : "—"}
                                    </div>
                                    <div className="text-overline text-muted-foreground">Conversion</div>
                                </div>
                            </div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-2">
                            <Button
                                variant="default"
                                size="sm"
                                onClick={handleDownload}
                                disabled={downloading || !imgUrl}
                                data-testid="download-qr-btn"
                            >
                                <Download size={14} weight="regular" className="mr-1" />
                                {downloading ? "Preparing…" : "Download"}
                            </Button>
                            <Button
                                variant="quiet"
                                size="sm"
                                onClick={() => setConfirmOpen(true)}
                                disabled={regenerating}
                                data-testid="regenerate-qr-btn"
                            >
                                <ArrowClockwise size={14} weight="regular" className="mr-1" />
                                {regenerating ? "Regenerating..." : "Regenerate QR"}
                            </Button>
                        </div>
                    </div>
                )}
                <ConfirmDialog
                    open={confirmOpen}
                    onOpenChange={setConfirmOpen}
                    testId="confirm-regenerate-qr"
                    title="Regenerate the QR code?"
                    description="The old code stops working."
                    confirmLabel="Regenerate QR"
                    cancelLabel="Keep current code"
                    onConfirm={handleRegenerate}
                />
            </CardContent>
        </Card>
    );
}