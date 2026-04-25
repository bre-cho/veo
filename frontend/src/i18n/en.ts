/**
 * English translation dictionary (secondary language).
 */
import type { TranslationKey } from "./vi";

const en: Record<TranslationKey, string> = {
  // Navigation
  nav_dashboard: "Dashboard",
  nav_script_upload: "Script Upload",
  nav_render_jobs: "Render Jobs",
  nav_settings: "Settings",
  nav_avatar_builder: "Avatar Builder",
  nav_marketplace: "Marketplace",
  nav_analytics: "Analytics",
  nav_wallet: "Wallet",
  nav_creator: "Creator",
  nav_strategy: "Strategy",
  nav_templates: "Templates",
  nav_production_studio: "Production Studio",
  nav_projects: "Projects",
  nav_autopilot: "Autopilot",
  nav_audio: "Audio",
  nav_governance: "Governance",

  // Home page
  home_eyebrow: "Render Factory",
  home_title: "Multi-provider video publishing monorepo",
  home_description:
    "Local stack for script upload preview, provider plan building, render queue orchestration, callback or poll completion, object storage, dashboard plane, incident feed, and job detail UI.",
  home_card_dashboard: "Dashboard Plane",
  home_card_dashboard_desc: "Overview, project creation, and workspace entry points",
  home_card_script_upload: "Script Upload",
  home_card_script_upload_desc: "Upload .txt / .docx → preview → edit → validate → create project",
  home_card_audio_studio: "Audio Studio",
  home_card_audio_studio_desc: "Voice profiles, breath-paced narration, background music, and audio mix workflow",
  home_card_autopilot: "Autopilot",
  home_card_autopilot_desc: "Kill switch, release gate, runtime controls, and notification plane",
  home_card_strategy: "Strategy",
  home_card_strategy_desc: "Enterprise strategy signals, directives, portfolio allocation, and SLA risk view",
  home_card_templates: "Templates",
  home_card_templates_desc: "Template library, extraction, reuse, batch generation, and analytics",
  home_card_projects: "Projects",
  home_card_projects_desc: "Project workspace, Veo 3.1 controls, render status, scene rerender, and output preview",
  home_card_governance: "Governance",
  home_card_governance_desc: "Execution scheduling, cooldowns, orchestration control, and policy promotion path",
  home_card_settings: "Settings",
  home_card_settings_desc: "Manage Google AI accounts with account rotation to run multiple accounts simultaneously",
  home_card_api_docs: "API Docs",

  // Dashboard / incidents
  dashboard_title: "Dashboard",
  dashboard_incidents: "Incidents",
  dashboard_no_incidents: "No incidents",
  dashboard_recent_events: "Recent Events",

  // Realtime progress
  realtime_progress_title: "Realtime Progress",
  realtime_no_events: "No events yet",

  // Rebuild decision panel
  rebuild_decision_title: "Rebuild Decision",
  rebuild_strategy: "Selected Strategy",
  rebuild_reason: "Rebuild Reason",
  rebuild_mandatory_scenes: "Mandatory Scenes",
  rebuild_optional_scenes: "Optional Scenes",
  rebuild_skipped_scenes: "Skipped Scenes",
  rebuild_estimated_cost: "Estimated Cost",
  rebuild_estimated_time: "Estimated Time",
  rebuild_warnings: "Warnings",
  rebuild_approve_btn: "Approve & Execute",
  rebuild_cancel_btn: "Cancel",
  rebuild_status_allow: "Allow",
  rebuild_status_downgrade: "Downgrade",
  rebuild_status_block: "Block",
  rebuild_no_decision: "No rebuild decision yet",
  rebuild_decision_loading: "Computing…",
  rebuild_budget_policy: "Budget Policy",

  // Budget policy selector
  budget_policy_cheap: "Cheap",
  budget_policy_balanced: "Balanced",
  budget_policy_quality: "Quality",
  budget_policy_emergency: "Emergency",
  budget_policy_label: "Budget Policy",
  budget_policy_description_cheap: "Low cost limit, allows downgrade",
  budget_policy_description_balanced: "Balance between cost and quality",
  budget_policy_description_quality: "No downgrade, includes optional scenes",
  budget_policy_description_emergency: "Minimal budget, aggressive downgrade",

  // Common
  loading: "Loading…",
  error: "Error",
  success: "Success",
  confirm: "Confirm",
  cancel: "Cancel",
  save: "Save",
  close: "Close",
  back: "Back",
  next: "Next",
  scene: "Scene",
  scenes: "Scenes",
  cost: "Cost",
  time: "Time",
  status: "Status",
  actions: "Actions",
};

export default en;
