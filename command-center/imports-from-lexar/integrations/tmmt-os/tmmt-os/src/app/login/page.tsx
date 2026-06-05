"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const supabase = createSupabaseBrowserClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(
    params.get("error") === "forbidden" ? "You don't have access to that portal." : null
  );
  const [mode, setMode] = useState<"password" | "magic">("password");

  async function onPasswordSignIn(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return setError(error.message);
    const next = params.get("next") || "/internal/dashboard";
    router.replace(next);
    router.refresh();
  }

  async function onMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    });
    if (error) return setError(error.message);
    setSent(true);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40">
      <Card className="w-full max-w-md p-6 space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">TMMT OS</h1>
          <p className="text-sm text-muted-foreground">Sign in to your portal</p>
        </div>

        <div className="flex gap-2 text-sm">
          <button
            type="button"
            onClick={() => setMode("password")}
            className={`px-3 py-1 rounded ${mode === "password" ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
          >
            Password
          </button>
          <button
            type="button"
            onClick={() => setMode("magic")}
            className={`px-3 py-1 rounded ${mode === "magic" ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
          >
            Magic link
          </button>
        </div>

        {sent ? (
          <p className="text-sm">Check your email — we sent you a sign-in link.</p>
        ) : (
          <form onSubmit={mode === "password" ? onPasswordSignIn : onMagicLink} className="space-y-3">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            {mode === "password" && (
              <div>
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full">
              {mode === "password" ? "Sign in" : "Send magic link"}
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
