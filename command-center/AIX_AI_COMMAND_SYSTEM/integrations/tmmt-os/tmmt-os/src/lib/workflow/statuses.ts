// =============================================================================
// Workflow vocabulary — keep in lock-step with supabase/migrations/0001_init.sql
// =============================================================================

export const USER_ROLES = ["admin", "internal_team", "investor", "vendor", "customer"] as const;
export type UserRole = (typeof USER_ROLES)[number];

export const CASE_STATUSES = [
  "intake_submitted",
  "initial_contact_needed",
  "initial_contact_complete",
  "internal_review",
  "task_assignment",
  "vendor_needed",
  "vendor_assigned",
  "vendor_in_progress",
  "vendor_completed",
  "internal_quality_check",
  "customer_follow_up",
  "awaiting_approval",
  "completed",
  "closed",
  "blocked",
] as const;
export type CaseStatus = (typeof CASE_STATUSES)[number];

export const VENDOR_JOB_STATUSES = [
  "offered",
  "accepted",
  "declined",
  "scheduled",
  "in_progress",
  "pending_review",
  "completed",
  "rejected",
  "paid",
  "cancelled",
] as const;
export type VendorJobStatus = (typeof VENDOR_JOB_STATUSES)[number];

export const REQUEST_TYPES = [
  "rental_booking",
  "rental_support",
  "maintenance",
  "repair",
  "detail",
  "tow",
  "inspection",
  "delivery",
  "content",
  "consulting",
  "other",
] as const;
export type RequestType = (typeof REQUEST_TYPES)[number];

/**
 * Forward-only happy-path transitions for cases. The DB doesn't enforce these
 * — they're the engine's "what should normally happen next" guide. Any staff
 * member can still set status manually via the case detail page.
 */
export const CASE_TRANSITIONS: Record<CaseStatus, CaseStatus[]> = {
  intake_submitted: ["initial_contact_needed", "internal_review", "blocked"],
  initial_contact_needed: ["initial_contact_complete", "blocked"],
  initial_contact_complete: ["internal_review"],
  internal_review: ["task_assignment", "vendor_needed", "awaiting_approval", "blocked", "completed"],
  task_assignment: ["vendor_needed", "internal_quality_check", "awaiting_approval"],
  vendor_needed: ["vendor_assigned", "blocked"],
  vendor_assigned: ["vendor_in_progress", "blocked"],
  vendor_in_progress: ["vendor_completed", "blocked"],
  vendor_completed: ["internal_quality_check"],
  internal_quality_check: ["customer_follow_up", "vendor_in_progress", "awaiting_approval"],
  customer_follow_up: ["awaiting_approval", "completed"],
  awaiting_approval: ["completed", "blocked"],
  completed: ["closed"],
  closed: [],
  blocked: ["internal_review", "closed"],
};

/** Map request type → suggested initial next status after intake. */
export function suggestedNextStatus(requestType: RequestType): CaseStatus {
  switch (requestType) {
    case "rental_booking":
    case "rental_support":
    case "consulting":
      return "initial_contact_needed";
    case "maintenance":
    case "repair":
    case "detail":
    case "tow":
    case "inspection":
    case "delivery":
    case "content":
      return "internal_review";
    default:
      return "initial_contact_needed";
  }
}

export const CASE_STATUS_LABEL: Record<CaseStatus, string> = {
  intake_submitted: "Intake submitted",
  initial_contact_needed: "Initial contact needed",
  initial_contact_complete: "Initial contact done",
  internal_review: "Internal review",
  task_assignment: "Task assignment",
  vendor_needed: "Vendor needed",
  vendor_assigned: "Vendor assigned",
  vendor_in_progress: "Vendor working",
  vendor_completed: "Vendor finished",
  internal_quality_check: "Quality check",
  customer_follow_up: "Customer follow-up",
  awaiting_approval: "Awaiting approval",
  completed: "Completed",
  closed: "Closed",
  blocked: "Blocked",
};

export const VENDOR_JOB_LABEL: Record<VendorJobStatus, string> = {
  offered: "Offered",
  accepted: "Accepted",
  declined: "Declined",
  scheduled: "Scheduled",
  in_progress: "In progress",
  pending_review: "Pending review",
  completed: "Completed",
  rejected: "Rejected by ops",
  paid: "Paid",
  cancelled: "Cancelled",
};

/** What the vendor is allowed to set themselves from each status. */
export const VENDOR_ALLOWED_TRANSITIONS: Record<VendorJobStatus, VendorJobStatus[]> = {
  offered: ["accepted", "declined"],
  accepted: ["scheduled", "in_progress"],
  scheduled: ["in_progress", "cancelled"],
  in_progress: ["pending_review"],
  pending_review: [],
  completed: [],
  rejected: [],
  declined: [],
  paid: [],
  cancelled: [],
};

/** Map vendor job state → the case status the parent case should reflect. */
export function caseStatusForVendorJob(s: VendorJobStatus): CaseStatus | null {
  switch (s) {
    case "offered":
    case "accepted":
    case "scheduled":
      return "vendor_assigned";
    case "in_progress":
      return "vendor_in_progress";
    case "pending_review":
    case "completed":
      return "vendor_completed";
    default:
      return null;
  }
}
