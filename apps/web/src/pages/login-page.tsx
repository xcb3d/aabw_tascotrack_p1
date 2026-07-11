import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, Mail, ShieldAlert } from "lucide-react";

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
      
      // Dispatch storage event to notify app shell
      window.dispatchEvent(new Event("storage"));
      
      // Redirect
      navigate("/assistant");
    } catch (err: any) {
      setError(err.message || "Kết nối đến máy chủ thất bại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 font-sans text-white">
      {/* Background gradients */}
      <div className="absolute top-[-20%] left-[-10%] h-[600px] w-[600px] rounded-full bg-violet-600/10 blur-[120px]" />
      <div className="absolute right-[-10%] bottom-[-20%] h-[600px] w-[600px] rounded-full bg-blue-600/10 blur-[120px]" />

      {/* Main glassmorphism card */}
      <div className="relative w-full max-w-[420px] rounded-2xl border border-white/10 bg-white/[0.03] p-8 shadow-2xl backdrop-blur-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400">
            <KeyRound className="size-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Đăng Nhập</h1>
          <p className="mt-1.5 text-xs text-slate-400">
            Hệ thống quản trị tri thức an toàn My Tasco Secure RAG
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          {error && (
            <div className="flex items-start gap-2.5 rounded-lg border border-red-500/20 bg-red-500/5 p-3.5 text-xs text-red-400">
              <ShieldAlert className="size-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">
              Mã User hoặc Email
            </label>
            <div className="relative">
              <Mail className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Ví dụ: U001, U007, hoặc email..."
                className="h-11 w-full rounded-lg border border-white/10 bg-white/5 pr-4 pl-10 text-sm placeholder:text-slate-500 focus:border-violet-500/50 focus:bg-white/10 focus:outline-none"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">
              Mật khẩu
            </label>
            <div className="relative">
              <KeyRound className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu bất kỳ để test..."
                className="h-11 w-full rounded-lg border border-white/10 bg-white/5 pr-4 pl-10 text-sm placeholder:text-slate-500 focus:border-violet-500/50 focus:bg-white/10 focus:outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex h-11 w-full items-center justify-center rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-sm font-semibold hover:from-violet-500 hover:to-indigo-500 focus:outline-none disabled:opacity-50"
          >
            {loading ? "Đang xử lý..." : "Đăng Nhập"}
          </button>
        </form>

        <div className="mt-6 text-center text-[10px] text-slate-500">
          Dữ liệu thử nghiệm tài khoản đã được nạp sẵn trong Database local.
        </div>
      </div>
    </div>
  );
}
