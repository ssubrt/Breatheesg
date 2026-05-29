'use client';

import { useState } from 'react';
import { patch } from '@/lib/api';
import { RawEmission } from '@/lib/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface EmissionModalProps {
  emission: RawEmission | null;
  onClose: () => void;
  onUpdate: () => void;
}

export default function EmissionModal({ emission, onClose, onUpdate }: EmissionModalProps) {
  const [notes, setNotes] = useState(emission?.analyst_notes || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);

  if (!emission) return null;

  const handleApprove = async () => {
    setLoading(true);
    setError('');

    const result = await patch(`/emissions/${emission.id}/approve/`, {
      notes: notes,
    });

    if ('error' in result || 'detail' in result) {
      setError(result.error || result.detail || 'Failed to approve');
    } else {
      onUpdate();
    }

    setLoading(false);
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      setError('Rejection reason required');
      return;
    }

    setLoading(true);
    setError('');

    const result = await patch(`/emissions/${emission.id}/reject/`, {
      reason: rejectionReason,
    });

    if ('error' in result || 'detail' in result) {
      setError(result.error || result.detail || 'Failed to reject');
    } else {
      onUpdate();
    }

    setLoading(false);
  };

  const handleSaveNotes = async () => {
    setLoading(true);
    setError('');

    const result = await patch(`/emissions/${emission.id}/update_notes/`, {
      notes: notes,
    });

    if ('error' in result || 'detail' in result) {
      setError(result.error || result.detail || 'Failed to save notes');
    } else {
      onUpdate();
    }

    setLoading(false);
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      NEW: 'bg-yellow-100 text-yellow-800',
      REVIEWED: 'bg-blue-100 text-blue-800',
      APPROVED: 'bg-green-100 text-green-800',
      REJECTED: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const isEditable = emission.status !== 'APPROVED';

  return (
    <Dialog open={!!emission} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Emission Record Details</DialogTitle>
          <DialogDescription>
            ID: {emission.id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Error */}
          {error && (
            <div className="flex gap-2 bg-destructive/10 border border-destructive/30 rounded-md p-3">
              <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Status Badge */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{emission.activity_type}</h3>
              <p className="text-sm text-muted-foreground">
                {new Date(emission.activity_date).toLocaleDateString()}
              </p>
            </div>
            <Badge className={getStatusColor(emission.status)}>
              {emission.status}
            </Badge>
          </div>

          {/* Activity Data */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Activity Data</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">Activity Value</p>
                  <p className="font-medium">{emission.activity_value} {emission.activity_unit}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Emission Factor</p>
                  <p className="font-medium">{emission.emission_factor} kg CO₂e per {emission.activity_unit}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Calculated Emissions</p>
                  <p className="font-medium text-lg">
                    {parseFloat(String(emission.calculated_emissions_kg_co2e)).toFixed(2)} kg CO₂e
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Category</p>
                  <p className="font-medium">{emission.category}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Scope</p>
                  <p className="font-medium">{emission.scope}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Source</p>
                  <p className="font-medium text-sm">{emission.data_source_filename || 'Manual'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Issues */}
          {emission.validation_issues && emission.validation_issues.length > 0 && (
            <Card className="border-amber-200 bg-amber-50">
              <CardHeader>
                <CardTitle className="text-base flex gap-2 items-center">
                  <AlertCircle className="h-5 w-5 text-amber-600" />
                  Validation Issues
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {emission.validation_issues.map((issue, idx) => (
                    <li key={idx} className="text-sm text-amber-900 flex gap-2">
                      <span>•</span>
                      {issue}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Audit Log */}
          {emission.audit_logs && emission.audit_logs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Audit Log</CardTitle>
                <CardDescription>Change history</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {emission.audit_logs.map((log) => (
                    <div key={log.id} className="text-sm p-2 border rounded-md">
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium">{log.action}</span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                      </div>
                      {log.changed_by_name && (
                        <p className="text-xs text-muted-foreground">by {log.changed_by_name}</p>
                      )}
                      {log.notes && (
                        <p className="text-xs mt-1">{log.notes}</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Notes */}
          {isEditable && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Analyst Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add notes about this record..."
                  rows={4}
                />
                <Button
                  onClick={handleSaveNotes}
                  variant="outline"
                  disabled={loading || notes === emission.analyst_notes}
                  size="sm"
                >
                  {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                  Save Notes
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Rejection Form */}
          {emission.status !== 'APPROVED' && emission.status !== 'REJECTED' && (
            <Card className={showRejectForm ? 'border-red-200 bg-red-50' : ''}>
              <CardHeader>
                <CardTitle className="text-base">Review Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {!showRejectForm ? (
                  <div className="flex gap-2">
                    <Button
                      onClick={handleApprove}
                      disabled={loading}
                      className="flex-1"
                    >
                      {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                      Approve
                    </Button>
                    <Button
                      onClick={() => setShowRejectForm(true)}
                      variant="outline"
                      disabled={loading}
                      className="flex-1"
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Textarea
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="Why are you rejecting this record?"
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <Button
                        onClick={handleReject}
                        variant="destructive"
                        disabled={loading || !rejectionReason.trim()}
                        className="flex-1"
                      >
                        {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                        Confirm Rejection
                      </Button>
                      <Button
                        onClick={() => {
                          setShowRejectForm(false);
                          setRejectionReason('');
                        }}
                        variant="outline"
                        disabled={loading}
                        className="flex-1"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Read-only Message for Approved */}
          {emission.status === 'APPROVED' && (
            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-6">
                <p className="text-sm text-green-900 flex gap-2">
                  <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
                  This record has been approved and cannot be modified.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
