import { Badge } from "@/components/ui/badge";
import { VENDOR_JOB_LABEL, type VendorJobStatus } from "@/lib/workflow/statuses";

const VARIANT: Record<VendorJobStatus, "default" | "secondary" | "outline" | "success" | "warning" | "destructive" | "info"> = {
  offered: "warning",
  accepted: "info",
  declined: "destructive",
  scheduled: "info",
  in_progress: "info",
  pending_review: "warning",
  completed: "success",
  rejected: "destructive",
  paid: "success",
  cancelled: "outline",
};

export function JobStatusBadge({ status }: { status: VendorJobStatus }) {
  return <Badge variant={VARIANT[status]}>{VENDOR_JOB_LABEL[status]}</Badge>;
}
