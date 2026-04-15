import { useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { TrendingUp, BarChart3, Sparkles, ShieldCheck, ArrowRight } from "lucide-react";
import choLogo from "@/assets/cho-group-logo.png";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const result = await login(username.trim(), password);
    if (!result.success) setError(result.error || "Login failed");
    setLoading(false);
  };

  const features = [
    { icon: TrendingUp, text: "Real-time retail price tracking", color: "from-primary/20 to-primary/5" },
    { icon: BarChart3, text: "Cross-store price comparisons", color: "from-accent/20 to-accent/5" },
    { icon: Sparkles, text: "AI-powered price forecasting", color: "from-primary/20 to-primary/5" },
    { icon: ShieldCheck, text: "Secure team-wide access control", color: "from-accent/20 to-accent/5" },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Left — Hero */}
      <div className="hidden lg:flex lg:w-[55%] relative overflow-hidden bg-sidebar flex-col justify-center px-16 xl:px-24">
        {/* Decorative */}
        <div className="absolute inset-0">
          <div className="absolute top-20 left-20 w-96 h-96 rounded-full bg-primary/10 blur-[120px]" />
          <div className="absolute bottom-20 right-20 w-72 h-72 rounded-full bg-accent/10 blur-[100px]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full border border-sidebar-border/30" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full border border-sidebar-border/20" />
        </div>

        <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7 }} className="relative z-10">
          <div className="flex items-center gap-4 mb-12">
            <div className="w-16 h-16 rounded-2xl overflow-hidden bg-white flex items-center justify-center shadow-xl shadow-primary/30">
              <img src={choLogo} alt="CHO Group" className="w-14 h-14 object-contain" />
            </div>
            <div>
              <h1 className="text-4xl font-black text-sidebar-accent-foreground tracking-tight">CHO MarketWatch</h1>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mt-1">Retail Price Intelligence</p>
            </div>
          </div>

          <p className="text-lg font-medium text-sidebar-foreground/60 mb-10 max-w-md leading-relaxed">
            Monitor, compare, and forecast olive oil prices across international retail markets.
          </p>

          <div className="grid grid-cols-2 gap-4 max-w-lg">
            {features.map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + i * 0.1, duration: 0.4 }}
                className={`p-4 rounded-2xl bg-gradient-to-br ${f.color} border border-sidebar-border/50 backdrop-blur-sm`}
              >
                <f.icon className="w-5 h-5 text-primary mb-3" />
                <p className="text-sm font-medium text-sidebar-foreground/80 leading-snug">{f.text}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right — Form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-background">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="w-full max-w-sm"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <div className="w-12 h-12 rounded-xl overflow-hidden bg-white flex items-center justify-center shadow-lg border border-border/60">
              <img src={choLogo} alt="CHO Group" className="w-10 h-10 object-contain" />
            </div>
            <span className="text-2xl font-bold text-foreground tracking-tight">CHO MarketWatch</span>
          </div>

          <div className="text-center lg:text-left mb-10">
            <h2 className="text-3xl font-black text-foreground tracking-tight">Welcome back</h2>
            <p className="text-muted-foreground mt-2 text-sm">Sign in to access your dashboard</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-xs font-bold text-foreground/70 uppercase tracking-wider mb-2 block">Username</label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                className="h-12 rounded-xl bg-secondary/50 border-border/50 focus:border-primary focus:ring-primary/20 transition-all"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-foreground/70 uppercase tracking-wider mb-2 block">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="h-12 rounded-xl bg-secondary/50 border-border/50 focus:border-primary focus:ring-primary/20 transition-all"
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-destructive/10 text-destructive text-sm font-semibold p-3 rounded-xl border border-destructive/20"
              >
                {error}
              </motion.div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-xl gradient-gold hover:opacity-90 text-primary-foreground font-bold text-sm shadow-lg shadow-primary/25 transition-all duration-200 group"
            >
              {loading ? "Signing in..." : (
                <span className="flex items-center gap-2">
                  Sign In <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </span>
              )}
            </Button>
          </form>

          <div className="mt-8 p-4 rounded-xl bg-muted/50 border border-border/50">
            <p className="text-[11px] text-muted-foreground text-center font-medium">
              Default account on a freshly initialized database: <span className="text-foreground font-semibold">admin/admin123</span>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
