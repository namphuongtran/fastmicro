/**
 * Audit Event Detail Component
 *
 * Displays detailed information about a single audit event
 * in a slide-over panel or modal.
 */
"use client";

import { format } from "date-fns";
import {
  X,
  User,
  Server,
  Clock,
  Tag,
  FileText,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

import type { AuditEvent } from "@/types/audit";
import {
  severityVariants,
  severityColors,
  actionLabels,
  severityLabels,
} from "@/types/audit";

// ============================================================================
// Types
// ============================================================================

interface AuditEventDetailProps {
  event: AuditEvent | null;
  open: boolean;
  onClose: () => void;
}

// ============================================================================
// Sub-components
// ============================================================================

function DetailRow({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  label: string;
  value: React.ReactNode;
  className?: string;
}) {
  if (!value) return null;

  return (
    <div className={cn("flex items-start gap-3 py-2", className)}>
      {Icon && (
        <Icon className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <dt className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </dt>
        <dd className="mt-0.5 text-sm">{value}</dd>
      </div>
    </div>
  );
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-6 w-6"
      onClick={handleCopy}
    >
      {copied ? (
        <Check className="h-3 w-3 text-green-500" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </Button>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function AuditEventDetail({
  event,
  open,
  onClose,
}: AuditEventDetailProps) {
  if (!event) return null;

  const timestamp = new Date(event.timestamp);

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent className="w-full sm:max-w-xl">
        <SheetHeader className="space-y-1">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-lg">Audit Event Details</SheetTitle>
          </div>
          <SheetDescription className="flex items-center gap-2 text-xs">
            <span className="font-mono">{event.id}</span>
            <CopyButton value={event.id} />
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] mt-6 -mr-4 pr-4">
          <div className="space-y-6">
            {/* Header Badges */}
            <div className="flex flex-wrap gap-2">
              <Badge
                variant={severityVariants[event.severity]}
                className={cn("text-xs", severityColors[event.severity])}
              >
                {severityLabels[event.severity]}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {actionLabels[event.action]}
              </Badge>
              {event.compliance_tags?.map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                >
                  {tag}
                </Badge>
              ))}
            </div>

            {/* Description */}
            {event.description && (
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-sm">{event.description}</p>
              </div>
            )}

            <Separator />

            {/* Timestamp */}
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Timestamp
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-xs text-muted-foreground">Date</dt>
                  <dd className="text-sm font-medium">
                    {format(timestamp, "PPPP")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Time</dt>
                  <dd className="text-sm font-medium">
                    {format(timestamp, "pp")}
                  </dd>
                </div>
              </div>
            </div>

            <Separator />

            {/* Actor Information */}
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <User className="h-4 w-4" />
                Actor
              </h4>
              <dl className="space-y-1">
                <DetailRow
                  label="ID"
                  value={
                    <div className="flex items-center gap-1">
                      <span className="font-mono text-xs">{event.actor_id}</span>
                      <CopyButton value={event.actor_id} />
                    </div>
                  }
                />
                {event.actor_name && (
                  <DetailRow label="Name" value={event.actor_name} />
                )}
                <DetailRow label="Type" value={event.actor_type} />
              </dl>
            </div>

            <Separator />

            {/* Resource Information */}
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Resource
              </h4>
              <dl className="space-y-1">
                <DetailRow label="Type" value={event.resource_type} />
                <DetailRow
                  label="ID"
                  value={
                    <div className="flex items-center gap-1">
                      <span className="font-mono text-xs">
                        {event.resource_id}
                      </span>
                      <CopyButton value={event.resource_id} />
                    </div>
                  }
                />
                {event.resource_name && (
                  <DetailRow label="Name" value={event.resource_name} />
                )}
              </dl>
            </div>

            <Separator />

            {/* Service Information */}
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Server className="h-4 w-4" />
                Source
              </h4>
              <dl className="space-y-1">
                <DetailRow label="Service" value={event.service_name} />
                {event.correlation_id && (
                  <DetailRow
                    label="Correlation ID"
                    value={
                      <div className="flex items-center gap-1">
                        <span className="font-mono text-xs">
                          {event.correlation_id}
                        </span>
                        <CopyButton value={event.correlation_id} />
                      </div>
                    }
                  />
                )}
              </dl>
            </div>

            {/* Compliance Tags */}
            {event.compliance_tags && event.compliance_tags.length > 0 && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Compliance
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {event.compliance_tags.map((tag) => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

export default AuditEventDetail;
