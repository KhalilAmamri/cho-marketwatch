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
    gold: "from-primary/20 to-primary/5 border-primary/20",
    teal: "from-accent/20 to-accent/5 border-accent/20",
    default: "from-secondary to-secondary/50 border-border/50",
  };

  const iconBg = {
    gold: "bg-primary/15 text-primary",
    teal: "bg-accent/15 text-accent",
    default: "bg-muted text-muted-foreground",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`glass-card-hover rounded-2xl p-5 bg-gradient-to-br ${accentClasses[accentColor]}`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-foreground tracking-tight">{value}</p>
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg[accentColor]}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      {trend && trendValue && (
        <div className="mt-3 flex items-center gap-1.5">
          <span className={`text-xs font-semibold ${trend === "up" ? "text-accent" : trend === "down" ? "text-destructive" : "text-muted-foreground"}`}>
            {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"} {trendValue}
          </span>
        </div>
      )}
    </motion.div>
  );
}
