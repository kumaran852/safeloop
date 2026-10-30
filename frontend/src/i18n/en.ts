export const en = {
  nav_dashboard: "Dashboard", nav_workers: "Workers", nav_reports: "Reports", nav_alerts: "Alerts", nav_cases: "Cases",
  nav_wards: "Ward intelligence", nav_analytics: "Analytics", nav_settings: "Settings", new_report: "New report",
  demo_banner: "Demo data is synthetic. No real worker information is stored.",
  form_title: "Report discomfort", form_intro: "Tell us where it hurts and about your work today. It takes about a minute.",
  worker_id: "Your worker ID", ward: "Ward", task: "Task", body_region: "Where do you feel discomfort?",
  discomfort: "How strong is the discomfort? (1 = very mild, 10 = worst)", shift_hours: "Hours worked in this shift", shift_type: "Shift",
  repetitive: "Do you repeat the same movements many times?", lifting: "Do you lift heavy things often?", yes: "Yes", no: "No",
  description: "Anything else you want to tell us? (optional)", submit: "Send report", sending: "Sending…",
  thanks_title: "Thank you. Your report was received.", thanks_body: "A supervisor will review it. Reporting does not lead to any penalty.",
  assessment: "Operator view: risk assessment", score: "Score", level: "Priority", why_score: "How the score was calculated",
  view_record: "View saved record", view_case: "Open case", another: "Send another report", choose: "Choose…", required: "This field is required",
  err_worker: "Enter a valid worker ID", err_severity: "Choose a level from 1 to 10", err_hours: "Enter hours between 1 and 16",
  dup_title: "This looks like a report already sent",
  dup_body: "A similar report from the same worker was saved in the last 24 hours. Send anyway?", send_anyway: "Send anyway", cancel: "Cancel",
  mild: "Mild", moderate_l: "Moderate", severe: "Severe", language: "Language", save: "Save", search: "Search",
} as const;
export type Key = keyof typeof en;
