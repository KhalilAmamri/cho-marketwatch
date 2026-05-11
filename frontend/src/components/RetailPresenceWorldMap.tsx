import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";

import { cn } from "@/lib/utils";
import type { RetailPresenceCountryMetric } from "@/lib/api";

// Nordic countries coordinates for map zoom (extend as needed when adding new countries)
const COUNTRY_COORDS: Record<string, [number, number]> = {
  Sweden: [18.6435, 60.1282],
  Finland: [25.7482, 61.9241],
  Norway: [8.4689, 60.472],
  Denmark: [9.5018, 56.2639],
};

type MapDatum = {
  name: string;
  value: number;
  websitesCount: number;
  presentCells: number;
  totalMatrixCells: number;
  coverageRate: number;
  iso3: string | null;
};

function formatPct(value: number): string {
  if (!Number.isFinite(value)) return "0.00%";
  return `${value.toFixed(2)}%`;
}

type ThemeColors = {
  background: string;
  foreground: string;
  muted: string;
  mutedForeground: string;
  border: string;
  primary: string;
  primary35: string;
  primary45: string;
  choTeal: string;
};

function toEchartsHsl(raw: string): { h: string; s: string; l: string; a: string | null } | null {
  const [hslPart, alphaPart] = raw.split("/").map((chunk) => chunk.trim());
  const parts = hslPart.split(/\s+/).filter(Boolean);
  if (parts.length < 3) return null;

  const [h, s, l] = parts;
  return { h, s, l, a: alphaPart || null };
}

function readHslVar(varName: string): string | null {
  if (typeof window === "undefined") return null;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  if (!raw) return null;

  const parsed = toEchartsHsl(raw);
  if (!parsed) return null;

  const { h, s, l, a } = parsed;
  if (a) return `hsla(${h}, ${s}, ${l}, ${a})`;
  return `hsl(${h}, ${s}, ${l})`;
}

function readHslVarWithAlpha(varName: string, alpha: number): string | null {
  if (typeof window === "undefined") return null;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  if (!raw) return null;

  const parsed = toEchartsHsl(raw);
  if (!parsed) return null;

  const { h, s, l } = parsed;
  return `hsla(${h}, ${s}, ${l}, ${alpha})`;
}

export function RetailPresenceWorldMap({
  metrics,
  selectedCountry,
  onSelectCountry,
  className,
}: {
  metrics: RetailPresenceCountryMetric[];
  selectedCountry?: string;
  onSelectCountry: (country: string) => void;
  className?: string;
}) {
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [themeColors, setThemeColors] = useState<ThemeColors | null>(null);

  useEffect(() => {
    const background = readHslVar("--background");
    const foreground = readHslVar("--foreground");
    const muted = readHslVar("--muted");
    const mutedForeground = readHslVar("--muted-foreground");
    const border = readHslVar("--border");
    const primary = readHslVar("--primary");
    const choTeal = readHslVar("--cho-teal");

    const primary35 = readHslVarWithAlpha("--primary", 0.35);
    const primary45 = readHslVarWithAlpha("--primary", 0.45);

    if (!background || !foreground || !muted || !mutedForeground || !border || !primary || !choTeal || !primary35 || !primary45) {
      setThemeColors(null);
      return;
    }

    setThemeColors({
      background,
      foreground,
      muted,
      mutedForeground,
      border,
      primary,
      primary35,
      primary45,
      choTeal,
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadWorldGeo() {
      try {
        setMapError(null);
        const res = await fetch("/maps/world.json", { cache: "force-cache" });
        if (!res.ok) throw new Error(`Failed to load world.json (${res.status})`);
        const geoJson = await res.json();
        if (cancelled) return;

        echarts.registerMap("world", geoJson);
        setMapReady(true);
      } catch (err: unknown) {
        if (cancelled) return;
        setMapError(err instanceof Error ? err.message : "Failed to load world map");
        setMapReady(false);
      }
    }

    loadWorldGeo();

    return () => {
      cancelled = true;
    };
  }, []);

  const data: MapDatum[] = useMemo(() => {
    return (metrics || []).map((row) => ({
      name: row.country,
      value: row.coverageRate,
      websitesCount: row.websitesCount,
      presentCells: row.presentCells,
      totalMatrixCells: row.totalMatrixCells,
      coverageRate: row.coverageRate,
      iso3: row.iso3,
    }));
  }, [metrics]);

  const metricNames = useMemo(() => new Set(data.map((d) => d.name)), [data]);

  // Calculate center and zoom based on countries with data
  const { center, zoom } = useMemo(() => {
    if (data.length === 0) {
      return { center: [20, 50], zoom: 1 }; // Default world view
    }

    // Get coordinates for countries with data
    const coords = data
      .map((d) => COUNTRY_COORDS[d.name])
      .filter((c): c is [number, number] => !!c);

    if (coords.length === 0) {
      return { center: [20, 50], zoom: 1 };
    }

    // Calculate bounding box
    const lngs = coords.map((c) => c[0]);
    const lats = coords.map((c) => c[1]);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);

    // Calculate center
    const centerLng = (minLng + maxLng) / 2;
    const centerLat = (minLat + maxLat) / 2;

    // Calculate zoom based on spread
    const lngSpread = maxLng - minLng;
    const latSpread = maxLat - minLat;
    const maxSpread = Math.max(lngSpread, latSpread);

    // Adjust zoom based on spread (smaller spread = higher zoom)
    let zoom = 1;
    if (maxSpread < 10) {
      zoom = 5; // Single country or very close countries
    } else if (maxSpread < 30) {
      zoom = 3; // Regional cluster (e.g., Europe)
    } else if (maxSpread < 60) {
      zoom = 2; // Continental
    } else {
      zoom = 1; // Global
    }

    return { center: [centerLng, centerLat], zoom };
  }, [data]);

  const option = useMemo(() => {
    if (!mapReady || !themeColors) return null;

    const { background, foreground, muted, mutedForeground, border, primary, primary35, primary45, choTeal } = themeColors;
    const selected = selectedCountry || "";

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        borderWidth: 1,
        borderColor: border,
        backgroundColor: background,
        textStyle: {
          color: foreground,
          fontSize: 12,
        },
        formatter: (params: unknown) => {
          const p = (params && typeof params === "object" ? (params as Record<string, unknown>) : {}) as Record<
            string,
            unknown
          >;
          const d = p.data as MapDatum | undefined;
          const name = String(p.name || "");

          if (!d) {
            return `<div style="font-weight:600; margin-bottom:4px;">${name}</div><div style="color: ${mutedForeground};">No tracked websites</div>`;
          }

          const iso3 = d.iso3 ? ` (${d.iso3})` : "";
          return [
            `<div style="font-weight:700; margin-bottom:4px;">${d.name}${iso3}</div>`,
            `<div><span style="color:${mutedForeground};">Coverage</span>: <b>${formatPct(d.coverageRate)}</b></div>`,
            `<div><span style="color:${mutedForeground};">Tracked websites</span>: <b>${d.websitesCount}</b></div>`,
            `<div><span style="color:${mutedForeground};">Signals</span>: <b>${d.presentCells}</b> / ${d.totalMatrixCells}</div>`,
          ].join("");
        },
      },
      visualMap: {
        min: 0,
        max: 100,
        calculable: false,
        orient: "horizontal",
        left: 10,
        bottom: 8,
        text: ["High", "Low"],
        textStyle: {
          color: mutedForeground,
        },
        inRange: {
          color: [muted, choTeal],
        },
        outOfRange: {
          color: [muted],
        },
      },
      geo: {
        map: "world",
        roam: true,
        center: center as [number, number],
        zoom: zoom,
        top: 8,
        left: 8,
        right: 8,
        bottom: 34,
        scaleLimit: { min: 1, max: 10 },
        label: { show: false },
        itemStyle: {
          borderColor: border,
          borderWidth: 0.6,
          areaColor: muted,
        },
        emphasis: {
          label: { show: false },
          itemStyle: {
            areaColor: primary35,
            borderColor: primary,
            borderWidth: 1,
          },
        },
        select: {
          itemStyle: {
            areaColor: primary45,
            borderColor: primary,
            borderWidth: 1.4,
          },
        },
      },
      series: [
        {
          type: "map",
          map: "world",
          geoIndex: 0,
          selectedMode: "single",
          center: center as [number, number],
          zoom: zoom,
          data: data.map((d) => ({
            ...d,
            selected: d.name === selected,
          })),
        },
      ],
    };
  }, [data, mapReady, selectedCountry, themeColors, center, zoom]);

  if (mapError) {
    return (
      <div className={cn("rounded-2xl border border-border/50 bg-background/60 p-4 text-sm text-muted-foreground", className)}>
        {mapError}
      </div>
    );
  }

  if (!option) {
    return (
      <div className={cn("rounded-2xl border border-border/50 bg-background/60 p-4 text-sm text-muted-foreground", className)}>
        Loading world map...
      </div>
    );
  }

  return (
    <ReactECharts
      className={className}
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height: 320, width: "100%" }}
      onEvents={{
        click: (params: unknown) => {
          const p = (params && typeof params === "object" ? (params as Record<string, unknown>) : {}) as Record<
            string,
            unknown
          >;
          const name = String(p.name || "").trim();
          if (!name) return;
          if (!metricNames.has(name)) return;
          onSelectCountry(name);
        },
      }}
    />
  );
}
