import { Badge } from "@/components/ui/badge";
import { CASE_STATUS_LABEL, type CaseStatus } from "@/lib/workflow/statuses";

const VARIANT: Record<CaseStatus, "default" | "secondary" | "outline" | "success" | "warning" | "destructive" | "info"> = {
  intake_submitted: "info",
  initial_contact_needed: "warning",
  initial_contact_complete: "secondary",
  internal_review: "secondary",
  task_assignment: "secondary",
  vendor_needed: "warning",
  vendor_assigned: "info",
  vendor_in_progress: "info",
  vendor_completed: "info",
  internal_quality_check: "warning",
  customer_follow_up: "warning",
  awaiting_approval: "warning",
  completed: "success",
  closed: "outline",
  blocked: "destructive",
};

export function CaseStatusBadge({ status }: { status: CaseStatus }) {
  return <Badge variant={VARIANT[status]}>{CASE_STATUS_LABEL[status]}</Badge>;
}
