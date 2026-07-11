import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError("Vui lòng nhập Username hoặc Email");
      return;
    }
    if (!password) {
      setError("Vui lòng nhập mật khẩu");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const resp = await fetch("/mytasco/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-App-Code": "MYTASCO"
        },
        body: JSON.stringify({ username, password })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail?.message || "Tên đăng nhập hoặc mật khẩu không đúng.");
      }

      // Save token and user info
      localStorage.setItem("tasco-token", data.body.token);
      localStorage.setItem("tasco-user", JSON.stringify(data.body.user));
      
      // Dispatch custom event to notify parent App component
      window.dispatchEvent(new Event("tasco-auth-changed"));
      
      // Redirect
      navigate("/assistant");
    } catch (err: any) {
      setError(err.message || "Kết nối đến máy chủ thất bại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4 font-sans text-[#172126] transition-all">
      {/* Container card matching the brand theme */}
      <div className="glass-panel w-full max-w-[400px] rounded-2xl border border-[#dce2e5] p-8 stagger">
        
        {/* Brand identity matching the Sidebar layout logo */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="grid size-10 place-items-center rounded-xl bg-[#d2e4e9] text-[#163b4a] font-extrabold text-lg">
            T
          </div>
          <div className="text-left">
            <p className="font-display text-[16px] font-extrabold leading-tight text-[#172126]">MY TASCO</p>
            <p className="text-[10px] font-bold tracking-[.2em] text-[#64737a]">AI WORKSPACE</p>
          </div>
        </div>

        <div className="mb-6 text-center">
          <h2 className="font-display text-lg font-bold tracking-tight text-[#172126]">Xác thực tài khoản</h2>
          <p className="mt-1 text-xs text-[#64737a]">
            Hệ thống quản trị tri thức an toàn RAG
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          {error && (
            <div className="flex items-start gap-2.5 rounded-lg border border-destructive/20 bg-destructive/5 p-3.5 text-xs text-destructive">
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="username" className="text-[10px] font-bold uppercase tracking-[.16em] text-[#64737a]">
              Mã nhân viên / Email
            </Label>
            <div className="relative">
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nhập U001, U007, hoặc email..."
                className="border-[#dce2e5] focus:border-[#2d6d86] focus:ring-1 focus:ring-[#2d6d86]"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-[10px] font-bold uppercase tracking-[.16em] text-[#64737a]">
              Mật khẩu
            </Label>
            <div className="relative">
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu (tasco123)"
                className="border-[#dce2e5] focus:border-[#2d6d86] focus:ring-1 focus:ring-[#2d6d86]"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-[#1f5368] hover:bg-[#163b4a] text-white shadow-sm mt-2 transition"
          >
            {loading ? "Đang kết nối..." : "Đăng Nhập"}
          </Button>
        </form>

        <div className="mt-6 text-center text-[10px] text-[#64737a]">
          Mật khẩu mặc định cho toàn bộ nhân viên là <strong className="font-semibold text-primary">tasco123</strong>.
        </div>
      </div>
    </div>
  );
}
