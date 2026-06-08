import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { qrApi } from "@/lib/api";
import { QrCode, ArrowClockwise, Download } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function QRCodeCard({ classId, className }) {
    const [qr, setQr] = useState(null);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(false);
    const [regenerating, setRegenerating] = useState(false);

    const load = async () => {
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
    };

    useEffect(() => {
        if (classId) load();
    }, [classId]);

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

    if (loading) {
        return <div className="h-40 animate-pulse border border-border bg-muted/40 rounded-lg" />;
    }

    return (
        <Card className="border border-border" data-testid={`qr-card-${classId}`}>
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-base">
                    <span className="flex items-center gap-2">
                        <QrCode size={16} weight="duotone" className="text-primary" />
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
                        <Button onClick={handleGenerate} size="sm" data-testid="generate-qr-btn">
                            Generate QR Code
                        </Button>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-4">
                        {/* QR Image */}
                        <div className="border border-border bg-white p-3 rounded">
                            <img
                                src={qrApi.downloadUrl(classId)}
                                alt={`QR code for ${className}`}
                                className="h-40 w-40"
                                data-testid="qr-image"
                            />
                        </div>

                        {/* Analytics row */}
                        {analytics && (
                            <div className="flex gap-6 text-center">
                                <div>
                                    <div className="font-display text-xl font-bold">
                                        {analytics.scan_count}
                                    </div>
                                    <div className="text-overline text-muted-foreground">Scans</div>
                                </div>
                                <div>
                                    <div className="font-display text-xl font-bold">
                                        {analytics.enrollment_count}
                                    </div>
                                    <div className="text-overline text-muted-foreground">Enrolled</div>
                                </div>
                                <div>
                                    <div className="font-display text-xl font-bold">
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
                            <Button variant="outline" size="sm" asChild data-testid="download-qr-btn">
                                <a href={qrApi.downloadUrl(classId)} download>
                                    <Download size={14} weight="duotone" className="mr-1" />
                                    Download
                                </a>
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleRegenerate}
                                disabled={regenerating}
                                data-testid="regenerate-qr-btn"
                            >
                                <ArrowClockwise size={14} weight="duotone" className="mr-1" />
                                {regenerating ? "Regenerating..." : "Regenerate"}
                            </Button>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}