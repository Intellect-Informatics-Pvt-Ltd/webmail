import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Eye, EyeOff, RefreshCw, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/settings/accounts")({
  component: AccountsSettings,
});

interface Pop3Config {
  host: string;
  port: number;
  username: string;
  tls_mode: string;
  connect_timeout_seconds: number;
  max_messages_per_poll: number;
}

interface Pop3Status {
  last_poll_at: string | null;
  last_poll_status: string;
  last_error: string | null;
  messages_last_cycle: number;
  is_polling: boolean;
}

function AccountsSettings() {
  // Form state
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState(1110);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [tlsMode, setTlsMode] = useState("none");
  const [showPassword, setShowPassword] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Status state
  const [status, setStatus] = useState<Pop3Status | null>(null);

  // Fetch current config on mount
  useEffect(() => {
    fetch("/api/v1/accounts/pop3")
      .then((r) => r.json())
      .then((data: Pop3Config) => {
        setHost(data.host);
        setPort(data.port);
        setUsername(data.username);
        setTlsMode(data.tls_mode);
      })
      .catch(() => {
        // Use defaults if API not available
      });
  }, []);

  // Poll status every 30s
  const fetchStatus = useCallback(() => {
    fetch("/api/v1/accounts/pop3/status")
      .then((r) => r.json())
      .then((data: Pop3Status) => setStatus(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleTestConnection = async () => {
    setIsTesting(true);
    try {
      const res = await fetch("/api/v1/accounts/pop3/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          host,
          port,
          username,
          password: password || undefined,
          tls_mode: tlsMode,
        }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        toast.success("Connection successful", {
          description: `Latency: ${data.latency_ms?.toFixed(1)}ms`,
        });
      } else {
        toast.error("Connection failed", {
          description: data.message || "Unable to connect to POP3 server",
        });
      }
    } catch {
      toast.error("Connection failed", {
        description: "Network error \u2014 is the backend running?",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const body: Record<string, unknown> = {
        host,
        port,
        username,
        tls_mode: tlsMode,
      };
      if (password) {
        body.password = password;
      }
      const res = await fetch("/api/v1/accounts/pop3", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        toast.success("POP3 settings saved");
      } else {
        toast.error("Failed to save", {
          description: "Server returned an error",
        });
      }
    } catch {
      toast.error("Failed to save", {
        description: "Network error",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSync = async () => {
    try {
      await fetch("/api/v1/accounts/pop3/sync", { method: "POST" });
      toast.success("Sync triggered");
      // Refresh status after a short delay
      setTimeout(fetchStatus, 2000);
    } catch {
      toast.error("Failed to trigger sync");
    }
  };

  const formatRelativeTime = (isoDate: string) => {
    const diff = Date.now() - new Date(isoDate).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <ScrollArea className="h-full w-full">
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <header>
          <h1 className="text-2xl font-bold tracking-tight">Accounts & sync</h1>
          <p className="text-sm text-muted-foreground">
            Configure your incoming mail server connection.
          </p>
        </header>

        {/* POP3 Configuration Card */}
        <Card>
          <CardHeader>
            <CardTitle>Incoming mail (POP3)</CardTitle>
            <CardDescription>
              Connect a POP3 server to receive mail in PSense.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="pop3-host">Server host</Label>
                <Input
                  id="pop3-host"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  placeholder="mail.example.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pop3-port">Port</Label>
                <Input
                  id="pop3-port"
                  type="number"
                  value={port}
                  onChange={(e) => setPort(Number(e.target.value))}
                  min={1}
                  max={65535}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pop3-username">Username</Label>
                <Input
                  id="pop3-username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="user@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pop3-password">Password</Label>
                <div className="relative">
                  <Input
                    id="pop3-password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Security</Label>
                <Select value={tlsMode} onValueChange={setTlsMode}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="ssl">SSL/TLS</SelectItem>
                    <SelectItem value="starttls">STARTTLS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="outline"
                onClick={handleTestConnection}
                disabled={isTesting}
              >
                {isTesting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Test connection
              </Button>
              <Button onClick={handleSave} disabled={isSaving}>
                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Sync Status Card */}
        <Card>
          <CardHeader>
            <CardTitle>Sync status</CardTitle>
            <CardDescription>
              Monitor your POP3 polling activity.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {status ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  {status.last_poll_status === "ok" && (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                      <span className="text-sm">
                        Last synced{" "}
                        {status.last_poll_at
                          ? formatRelativeTime(status.last_poll_at)
                          : "never"}
                      </span>
                    </>
                  )}
                  {status.last_poll_status === "error" && (
                    <>
                      <XCircle className="h-4 w-4 text-destructive" />
                      <span className="text-sm text-destructive">
                        Sync error
                      </span>
                    </>
                  )}
                  {status.last_poll_status === "never" && (
                    <span className="text-sm text-muted-foreground">
                      No sync has run yet
                    </span>
                  )}
                  {status.is_polling && (
                    <Badge variant="secondary" className="ml-auto">
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      Syncing
                    </Badge>
                  )}
                </div>

                {status.last_poll_status === "ok" && (
                  <p className="text-xs text-muted-foreground">
                    {status.messages_last_cycle} message
                    {status.messages_last_cycle !== 1 ? "s" : ""} fetched in last
                    cycle
                  </p>
                )}

                {status.last_error && (
                  <p className="text-xs text-destructive">{status.last_error}</p>
                )}

                <Button variant="outline" size="sm" onClick={handleSync}>
                  <RefreshCw className="mr-2 h-3 w-3" />
                  Sync now
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Loading status...</p>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}
