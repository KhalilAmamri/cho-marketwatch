import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  eyebrow?: string;
  /** Merged with default shell spacing; use for denser analytics pages. */
  className?: string;
}

export function PageHeader({ icon: Icon, title, subtitle, action, eyebrow = "Dashboard", className }: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={cn(
        "mb-5 section-shell p-4 md:p-5 flex flex-col md:flex-row md:items-start justify-between gap-3",
        className,
      )}
    >
      <div className="flex items-start gap-4 min-w-0">
        <div className="w-10 h-10 md:w-11 md:h-11 rounded-2xl gradient-gold flex items-center justify-center shadow-sm shadow-primary/20 flex-shrink-0">
          <Icon className="w-5 h-5 text-primary-foreground" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.18em] font-bold text-muted-foreground">{eyebrow}</p>
          <h1 className="text-[1.7rem] md:text-[1.85rem] font-bold text-foreground tracking-tight leading-tight mt-1 truncate">{title}</h1>
          {subtitle && <p className="text-sm text-muted-foreground mt-1 max-w-3xl leading-snug">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="md:pt-1 shrink-0">{action}</div>}
    </motion.div>
  );
}
