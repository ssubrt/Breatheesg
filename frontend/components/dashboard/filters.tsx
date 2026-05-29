'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { X } from 'lucide-react';

interface DashboardFiltersProps {
  filters: {
    status: string;
    scope: string;
    category: string;
    date_from: string;
    date_to: string;
    has_issues: string;
  };
  setFilters: (filters: any) => void;
}

export default function DashboardFilters({ filters, setFilters }: DashboardFiltersProps) {
  const handleStatusChange = (value: string) => {
    setFilters({ ...filters, status: value });
  };

  const handleScopeChange = (value: string) => {
    setFilters({ ...filters, scope: value === 'ALL' ? '' : value });
  };

  const handleCategoryChange = (value: string) => {
    setFilters({ ...filters, category: value === 'ALL' ? '' : value });
  };

  const handleDateFromChange = (value: string) => {
    setFilters({ ...filters, date_from: value });
  };

  const handleDateToChange = (value: string) => {
    setFilters({ ...filters, date_to: value });
  };

  const handleHasIssuesChange = (value: string) => {
    setFilters({ ...filters, has_issues: value === 'ALL' ? '' : value });
  };

  const handleReset = () => {
    setFilters({
      status: 'NEW,REVIEWED,APPROVED,REJECTED',
      scope: '',
      category: '',
      date_from: '',
      date_to: '',
      has_issues: '',
    });
  };

  const hasActiveFilters =
    filters.scope ||
    filters.category ||
    filters.date_from ||
    filters.date_to ||
    filters.has_issues ||
    filters.status !== 'NEW,REVIEWED,APPROVED,REJECTED';

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Status */}
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select value={filters.status} onValueChange={handleStatusChange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="NEW,REVIEWED,APPROVED,REJECTED">All</SelectItem>
                  <SelectItem value="NEW">New</SelectItem>
                  <SelectItem value="REVIEWED">Reviewed</SelectItem>
                  <SelectItem value="APPROVED">Approved</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Scope */}
            <div>
              <label className="text-sm font-medium mb-2 block">Scope</label>
              <Select value={filters.scope || 'ALL'} onValueChange={handleScopeChange}>
                <SelectTrigger>
                  <SelectValue placeholder="All scopes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Scopes</SelectItem>
                  <SelectItem value="SCOPE_1">Scope 1</SelectItem>
                  <SelectItem value="SCOPE_2">Scope 2</SelectItem>
                  <SelectItem value="SCOPE_3">Scope 3</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Category */}
            <div>
              <label className="text-sm font-medium mb-2 block">Category</label>
              <Select value={filters.category || 'ALL'} onValueChange={handleCategoryChange}>
                <SelectTrigger>
                  <SelectValue placeholder="All categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Categories</SelectItem>
                  <SelectItem value="FUEL">Fuel</SelectItem>
                  <SelectItem value="ELECTRICITY">Electricity</SelectItem>
                  <SelectItem value="FLIGHTS">Flights</SelectItem>
                  <SelectItem value="HOTELS">Hotels</SelectItem>
                  <SelectItem value="GROUND_TRANSPORT">Ground Transport</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Issues */}
            <div>
              <label className="text-sm font-medium mb-2 block">Validation</label>
              <Select value={filters.has_issues || 'ALL'} onValueChange={handleHasIssuesChange}>
                <SelectTrigger>
                  <SelectValue placeholder="All records" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Records</SelectItem>
                  <SelectItem value="true">With Issues</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">From Date</label>
              <Input
                type="date"
                value={filters.date_from}
                onChange={(e) => handleDateFromChange(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">To Date</label>
              <Input
                type="date"
                value={filters.date_to}
                onChange={(e) => handleDateToChange(e.target.value)}
              />
            </div>
          </div>

          {/* Reset Button */}
          {hasActiveFilters && (
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
              >
                <X className="h-4 w-4 mr-1" />
                Clear Filters
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
