"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useT } from "@/src/i18n/useT";
import type { TranslationKey } from "@/src/i18n/vi";

type NavItem = {
  labelKey: TranslationKey;
  href: string;
  descKey: TranslationKey;
};

const navItems: NavItem[] = [
  { labelKey: "nav_dashboard", href: "/", descKey: "home_card_dashboard_desc" },
  { labelKey: "nav_script_upload", href: "/script-upload", descKey: "home_card_script_upload_desc" },
  { labelKey: "nav_render_jobs", href: "/render-jobs", descKey: "sidebar_nav_desc_render_jobs" },
  { labelKey: "nav_settings", href: "/settings", descKey: "home_card_settings_desc" },
  { labelKey: "nav_avatar_builder", href: "/avatar-builder", descKey: "sidebar_nav_desc_avatar_builder" },
  { labelKey: "nav_marketplace", href: "/marketplace", descKey: "sidebar_nav_desc_marketplace" },
  { labelKey: "nav_analytics", href: "/analytics", descKey: "sidebar_nav_desc_analytics" },
  { labelKey: "nav_wallet", href: "/wallet", descKey: "sidebar_nav_desc_wallet" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const t = useT();

  return (
    <aside className="flex h-full w-full flex-col rounded-3xl border border-white/10 bg-black/20 p-4 text-white">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.25em] text-white/40">
          {t("sidebar_render_factory")}
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight">
          {t("sidebar_production_console")}
        </h2>
        <p className="mt-2 text-sm text-white/55">
          {t("sidebar_console_desc")}
        </p>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "block rounded-2xl border px-4 py-3 transition",
                isActive
                  ? "border-white/20 bg-white text-black"
                  : "border-white/10 bg-white/5 text-white hover:border-white/20 hover:bg-white/10",
              ].join(" ")}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{t(item.labelKey)}</p>
                  <p
                    className={[
                      "mt-1 text-xs",
                      isActive ? "text-black/70" : "text-white/55",
                    ].join(" ")}
                  >
                    {t(item.descKey)}
                  </p>
                </div>

                <span
                  className={[
                    "mt-0.5 inline-flex rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide",
                    isActive
                      ? "bg-black/10 text-black/70"
                      : "bg-white/10 text-white/50",
                  ].join(" ")}
                >
                  {isActive ? t("sidebar_active") : t("sidebar_open")}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-xs uppercase tracking-wide text-white/40">
          {t("sidebar_workflow")}
        </p>
        <div className="mt-3 space-y-2 text-sm text-white/65">
          <p>{t("sidebar_step_upload_script")}</p>
          <p>{t("sidebar_step_preview_edit")}</p>
          <p>{t("sidebar_step_validate")}</p>
          <p>{t("sidebar_step_render_plan")}</p>
          <p>{t("sidebar_step_track_jobs")}</p>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-xs uppercase tracking-wide text-white/40">
          {t("sidebar_avatar_workflow")}
        </p>
        <div className="mt-3 space-y-2 text-sm text-white/65">
          <p>{t("sidebar_step_build_dna")}</p>
          <p>{t("sidebar_step_choose_template")}</p>
          <p>{t("sidebar_step_launch_render")}</p>
          <p>{t("sidebar_step_track_performance")}</p>
          <p>{t("sidebar_step_earn_payout")}</p>
        </div>
      </div>
    </aside>
  );
}
