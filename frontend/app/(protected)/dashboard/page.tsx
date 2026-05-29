'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { get } from '@/lib/api';
import { RawEmission } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import EmissionModal from '@/components/dashboard/emission-modal';
import DashboardFilters from '@/components/dashboard/filters';
import { AlertCircle, Loader2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/';

export default function DashboardPage() {
  const [selectedEmission, setSelectedEmission] = useState<RawEmission | null>(null);
  const [filters, setFilters] = useState({
    status: 'NEW,REVIEWED,APPROVED,REJECTED',
    scope: '',
    category: '',
    date_from: '',
    date_to: '',
    has_issues: '',
  });

  const queryParams = new URLSearchParams();
  if (filters.status) queryParams.append('status', filters.status);
  if (filters.scope) queryParams.append('scope', filters.scope);
  if (filters.category) queryParams.append('category', filters.category);
  if (filters.date_from) queryParams.append('date_from', filters.date_from);
  if (filters.date_to) queryParams.append('date_to', filters.date_to);
  if (filters.has_issues) queryParams.append('has_issues', filters.has_issues);

  const { data: emissions, isLoading, error, mutate } = useSWR<RawEmission[]>(
    [`/emissions/?${queryParams.toString()}`, filters],
    async () => {
      const result = await get<{ count: number; results: RawEmission[] } | RawEmission[]>(`/emissions/?${queryParams.toString()}`);
      if ('error' in result) return [];
      if ('results' in result) return result.results; // paginated response
      if (Array.isArray(result)) return result;        // plain array
      return [];
    }
  );

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      NEW: 'bg-yellow-100 text-yellow-800',
      REVIEWED: 'bg-blue-100 text-blue-800',
      APPROVED: 'bg-green-100 text-green-800',
      REJECTED: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Review Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Manage and approve emissions records
        </p>
      </div>

      {/* Filters */}
      <DashboardFilters filters={filters} setFilters={setFilters} />

      {/* Emissions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Emissions Records</CardTitle>
          <CardDescription>
            {emissions?.length || 0} record{(emissions?.length || 0) !== 1 ? 's' : ''}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="flex gap-2 bg-destructive/10 border border-destructive/30 rounded-md p-3 mb-4">
              <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
              <p className="text-sm text-destructive">Failed to load emissions</p>
            </div>
          )}

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : emissions && emissions.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Emissions (kg CO₂e)</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Issues</TableHead>
                    <TableHead className="w-20">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {emissions.map((emission) => (
                    <TableRow key={emission.id}>
                      <TableCell className="text-sm">
                        {new Date(emission.activity_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-sm">
                        {emission.data_source_filename || 'Manual'}
                      </TableCell>
                      <TableCell className="text-sm">{emission.activity_type}</TableCell>
                      <TableCell className="text-sm">
                        {emission.activity_value} {emission.activity_unit}
                      </TableCell>
                      <TableCell className="text-sm font-medium">
                        {parseFloat(String(emission.calculated_emissions_kg_co2e)).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(emission.status)}>
                          {emission.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {emission.validation_issues?.length > 0 ? (
                          <Badge variant="outline" className="bg-amber-50">
                            {emission.validation_issues.length} issue{emission.validation_issues.length !== 1 ? 's' : ''}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedEmission(emission)}
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No records found</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal */}
      <EmissionModal
        emission={selectedEmission}
        onClose={() => setSelectedEmission(null)}
        onUpdate={() => {
          mutate();
          setSelectedEmission(null);
        }}
      />
    </div>
  );
}
