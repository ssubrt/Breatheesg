'use client';

import { useState } from 'react';
import { post } from '@/lib/api';
import { IngestionResponse } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export default function TravelUpload() {
  const [jsonContent, setJsonContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestionResponse | null>(null);
  const [error, setError] = useState('');

  const handleUpload = async () => {
    if (!jsonContent.trim()) {
      setError('Please paste JSON data');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const response = await post<IngestionResponse>('/ingestion/travel/', {
      content: jsonContent,
    });

    if ('error' in response || 'detail' in response) {
      setError(response.error || response.detail || 'Upload failed');
    } else {
      setResult(response);
      setJsonContent('');
    }

    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <label htmlFor="json-paste" className="block text-sm font-medium mb-2">
          Paste JSON Data
        </label>
        <Textarea
          id="json-paste"
          placeholder={`[
  {
    "expense_date": "2024-01-15",
    "expense_type": "FLIGHT",
    "origin_code": "SFO",
    "destination_code": "LHR",
    "cabin_class": "ECONOMY",
    "distance_km": 8600
  },
  {
    "expense_date": "2024-01-16",
    "expense_type": "HOTEL",
    "city": "London",
    "nights": 2
  }
]`}
          value={jsonContent}
          onChange={(e) => {
            setJsonContent(e.target.value);
            setError('');
            setResult(null);
          }}
          disabled={loading}
          rows={10}
          className="font-mono text-sm"
        />
      </div>

      {error && (
        <div className="flex gap-2 bg-destructive/10 border border-destructive/30 rounded-md p-3">
          <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <Button
        onClick={handleUpload}
        disabled={!jsonContent.trim() || loading}
        className="w-full"
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          'Upload JSON'
        )}
      </Button>

      {result && (
        <Card className={result.errors.length === 0 ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}>
          <CardHeader>
            <div className="flex items-center gap-2">
              {result.errors.length === 0 ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-600" />
              )}
              <CardTitle className="text-base">
                {result.ingested_count} records ingested
              </CardTitle>
            </div>
          </CardHeader>
        </Card>
      )}

      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-sm">JSON Format</CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-2">
          <p><strong>Flights:</strong> expense_date, expense_type (FLIGHT), origin_code, destination_code, cabin_class (ECONOMY/BUSINESS/FIRST), distance_km</p>
          <p><strong>Hotels:</strong> expense_date, expense_type (HOTEL), city, nights</p>
          <p><strong>Ground:</strong> expense_date, expense_type (GROUND/TAXI/etc), distance_km, transport_type</p>
          <p className="text-muted-foreground">All dates in YYYY-MM-DD format</p>
        </CardContent>
      </Card>
    </div>
  );
}
