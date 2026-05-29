'use client';

import { useState, useMemo } from 'react';
import useSWR from 'swr';
import { get } from '@/lib/api';
import { AnalyticsSummary } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, AlertCircle } from 'lucide-react';

const SCOPE_COLORS = {
  'SCOPE_1': '#ef4444',
  'SCOPE_2': '#f97316',
  'SCOPE_3': '#eab308',
};

const CATEGORY_COLORS = [
  '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e',
  '#f59e0b', '#10b981', '#06b6d4', '#6366f1',
];

export default function AnalyticsPage() {
  const [dateRange, setDateRange] = useState({
    from: '',
    to: '',
  });

  const queryParams = new URLSearchParams();
  if (dateRange.from) queryParams.append('date_from', dateRange.from);
  if (dateRange.to) queryParams.append('date_to', dateRange.to);

  const { data: analytics, isLoading, error } = useSWR<AnalyticsSummary>(
    [`/analytics/summary/?${queryParams.toString()}`, dateRange],
    async () => {
      const result = await get<AnalyticsSummary>(`/analytics/summary/?${queryParams.toString()}`);
      return 'error' in result ? undefined : result;
    }
  );

  const scopeData = useMemo(() => {
    if (!analytics) return [];
    return [
      { name: 'Scope 1', value: parseFloat(analytics.scope_1) },
      { name: 'Scope 2', value: parseFloat(analytics.scope_2) },
      { name: 'Scope 3', value: parseFloat(analytics.scope_3) },
    ].filter(item => item.value > 0);
  }, [analytics]);

  const categoryData = useMemo(() => {
    if (!analytics?.by_category) return [];
    return Object.entries(analytics.by_category)
      .map(([category, value]) => ({
        name: category,
        value: parseFloat(value),
      }))
      .sort((a, b) => b.value - a.value);
  }, [analytics]);

  const statusData = useMemo(() => {
    if (!analytics?.by_status) return [];
    return Object.entries(analytics.by_status).map(([status, count]) => ({
      name: status,
      value: count,
    }));
  }, [analytics]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground mt-1">
          Emissions summary and trends
        </p>
      </div>

      {error && (
        <div className="flex gap-2 bg-destructive/10 border border-destructive/30 rounded-md p-3">
          <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
          <p className="text-sm text-destructive">Failed to load analytics</p>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : analytics ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Total Emissions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {parseFloat(analytics.total_emissions_kg_co2e).toFixed(0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">kg CO₂e</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Scope 1</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {parseFloat(analytics.scope_1).toFixed(0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Direct Emissions</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Scope 2</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  {parseFloat(analytics.scope_2).toFixed(0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Indirect Energy</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Scope 3</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {parseFloat(analytics.scope_3).toFixed(0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Other Indirect</p>
              </CardContent>
            </Card>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Scope Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Emissions by Scope</CardTitle>
                <CardDescription>Distribution of emissions across scopes</CardDescription>
              </CardHeader>
              <CardContent>
                {scopeData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={scopeData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, value }) => `${name}: ${value.toFixed(0)}`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {scopeData.map((entry) => (
                          <Cell
                            key={`cell-${entry.name}`}
                            fill={SCOPE_COLORS[entry.name as keyof typeof SCOPE_COLORS] || '#ccc'}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => value.toFixed(2)} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No data available</p>
                )}
              </CardContent>
            </Card>

            {/* Category Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Emissions by Category</CardTitle>
                <CardDescription>Top emission categories</CardDescription>
              </CardHeader>
              <CardContent>
                {categoryData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={categoryData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                      <YAxis />
                      <Tooltip formatter={(value) => value.toFixed(2)} />
                      <Bar dataKey="value" fill="#3b82f6" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No data available</p>
                )}
              </CardContent>
            </Card>

            {/* Status Breakdown */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Records by Status</CardTitle>
                <CardDescription>Approval workflow progress</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {statusData.map((item) => (
                    <div key={item.name} className="p-4 border rounded-lg">
                      <p className="text-sm text-muted-foreground">{item.name}</p>
                      <p className="text-2xl font-bold">{item.value}</p>
                    </div>
                  ))}
                </div>
                {analytics.records_with_issues > 0 && (
                  <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md">
                    <p className="text-sm">
                      <span className="font-semibold">{analytics.records_with_issues}</span> record{analytics.records_with_issues !== 1 ? 's' : ''} with validation issues
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
