import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  accentColor?: "gold" | "teal" | "default";
}

export function MetricCard({ label, value, icon: Icon, trend, trendValue, accentColor = "default" }: MetricCardProps) {
  const accentClasses = {
    gold: "border-primary/35",
    teal: "border-accent/35",
    default: "border-border/75",
  };

  const iconBg = {
    gold: "bg-primary/12 text-primary",
    teal: "bg-accent/14 text-accent",
    default: "bg-muted/75 text-muted-foreground",
  };

  const trendTone = {
    up: "text-accent bg-accent/10 border-accent/25",
    down: "text-destructive bg-destructive/10 border-destructive/30",
    neutral: "text-muted-foreground bg-muted/50 border-border/60",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`kpi-shell rounded-2xl p-5 min-h-[118px] ${accentClasses[accentColor]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-[11px] leading-tight font-semibold text-muted-foreground uppercase tracking-[0.12em] break-words">{label}</p>
          <p className="text-[1.65rem] leading-tight font-bold text-foreground tracking-tight break-words">{value}</p>
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg[accentColor]}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {trendValue && trend && (
        <div className="mt-3 pt-3 border-t border-border/60 flex items-center justify-start">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${trendTone[trend]}`}>
            {trend === "up" ? "Up" : trend === "down" ? "Down" : "Flat"}
            <span className="text-foreground/80">{trendValue}</span>
          </span>
        </div>
      )}
    </motion.div>
  );
}
